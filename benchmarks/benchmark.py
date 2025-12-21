from __future__ import annotations

import csv
import os
import random
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

# Permite ejecutar el benchmark desde la carpeta del proyecto sin instalación.
PROYECTO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROYECTO_ROOT))

from src.avl import ArbolAVL  # noqa: E402
from src.vp_tree import ArbolProximidadVP, distancia_manhattan  # noqa: E402


@dataclass(frozen=True)
class ResultadoFila:
    experimento: str
    n: int
    m: int
    repeticiones: int
    build_ms_prom: float
    query_ms_prom: float
    query_ms_mediana: float
    extra: str


def _ms(segundos: float) -> float:
    return 1000.0 * float(segundos)


def _random_points(rng: random.Random, n: int, *, max_coord: int) -> list[tuple[int, int]]:
    return [(rng.randrange(0, max_coord), rng.randrange(0, max_coord)) for _ in range(n)]


def _linear_nearest(points: list[tuple[int, int]], q: tuple[int, int]) -> tuple[tuple[int, int] | None, int]:
    if not points:
        return None, 10**9
    best_p = points[0]
    best_d = distancia_manhattan(best_p, q)
    for p in points[1:]:
        d = distancia_manhattan(p, q)
        if d < best_d:
            best_d = d
            best_p = p
    return best_p, best_d


def bench_vptree_vs_lineal(
    *,
    tamanos: Iterable[int],
    m_consultas: int,
    repeticiones: int,
    semilla: int,
    max_coord: int,
) -> list[ResultadoFila]:
    filas: list[ResultadoFila] = []
    rng_base = random.Random(int(semilla))

    for n in tamanos:
        build_times: list[float] = []
        query_times_vp: list[float] = []
        query_times_lin: list[float] = []

        # Repeticiones con datos nuevos para evitar sesgos
        for _ in range(repeticiones):
            rng = random.Random(rng_base.randrange(0, 2**31 - 1))
            puntos = _random_points(rng, int(n), max_coord=int(max_coord))
            consultas = _random_points(rng, int(m_consultas), max_coord=int(max_coord))

            t0 = time.perf_counter()
            vp = ArbolProximidadVP(puntos, distancia=distancia_manhattan)
            t1 = time.perf_counter()
            build_times.append(_ms(t1 - t0))

            # Validación + tiempo VP-Tree
            t0 = time.perf_counter()
            vp_ds: list[int] = []
            for q in consultas:
                _p, d = vp.mas_cercano(q)
                vp_ds.append(int(d))
            t1 = time.perf_counter()
            query_times_vp.append(_ms(t1 - t0))

            # Tiempo lineal + validación
            t0 = time.perf_counter()
            lin_ds: list[int] = []
            for q in consultas:
                _p, d = _linear_nearest(puntos, q)
                lin_ds.append(int(d))
            t1 = time.perf_counter()
            query_times_lin.append(_ms(t1 - t0))

            if vp_ds != lin_ds:
                raise RuntimeError(
                    "VP-Tree y búsqueda lineal devolvieron distancias distintas; revisar implementación."
                )

        filas.append(
            ResultadoFila(
                experimento="VP-Tree (consultas)",
                n=int(n),
                m=int(m_consultas),
                repeticiones=int(repeticiones),
                build_ms_prom=float(statistics.fmean(build_times)),
                query_ms_prom=float(statistics.fmean(query_times_vp)),
                query_ms_mediana=float(statistics.median(query_times_vp)),
                extra="comparado contra lineal (mismo m)",
            )
        )
        filas.append(
            ResultadoFila(
                experimento="Lineal (consultas)",
                n=int(n),
                m=int(m_consultas),
                repeticiones=int(repeticiones),
                build_ms_prom=0.0,
                query_ms_prom=float(statistics.fmean(query_times_lin)),
                query_ms_mediana=float(statistics.median(query_times_lin)),
                extra="baseline O(n) por consulta",
            )
        )

    return filas


def bench_avl_vs_heapq(
    *,
    n: int,
    repeticiones: int,
    semilla: int,
) -> list[ResultadoFila]:
    import heapq

    filas: list[ResultadoFila] = []
    rng_base = random.Random(int(semilla))

    build_avl: list[float] = []
    pop_avl: list[float] = []
    build_heap: list[float] = []
    pop_heap: list[float] = []

    for _ in range(repeticiones):
        rng = random.Random(rng_base.randrange(0, 2**31 - 1))
        claves = [rng.random() for _ in range(int(n))]

        # AVL: insertar y extraer todo
        avl: ArbolAVL[float, int] = ArbolAVL()
        t0 = time.perf_counter()
        for i, k in enumerate(claves):
            avl.insertar(float(k), int(i))
        t1 = time.perf_counter()
        build_avl.append(_ms(t1 - t0))

        t0 = time.perf_counter()
        out1: list[float] = []
        while not avl.esta_vacio():
            k, _v = avl.extraer_minimo()
            out1.append(float(k))
        t1 = time.perf_counter()
        pop_avl.append(_ms(t1 - t0))

        # heapq
        heap: list[tuple[float, int]] = []
        t0 = time.perf_counter()
        for i, k in enumerate(claves):
            heapq.heappush(heap, (float(k), int(i)))
        t1 = time.perf_counter()
        build_heap.append(_ms(t1 - t0))

        t0 = time.perf_counter()
        out2: list[float] = []
        while heap:
            k, _v = heapq.heappop(heap)
            out2.append(float(k))
        t1 = time.perf_counter()
        pop_heap.append(_ms(t1 - t0))

        if out1 != out2:
            raise RuntimeError("AVL y heapq devolvieron orden distinto; revisar AVL.")

    filas.append(
        ResultadoFila(
            experimento="AVL (insert)",
            n=int(n),
            m=0,
            repeticiones=int(repeticiones),
            build_ms_prom=float(statistics.fmean(build_avl)),
            query_ms_prom=float(statistics.fmean(pop_avl)),
            query_ms_mediana=float(statistics.median(pop_avl)),
            extra="query_ms_* representa extraer_minimo() repetido n veces",
        )
    )
    filas.append(
        ResultadoFila(
            experimento="heapq (insert)",
            n=int(n),
            m=0,
            repeticiones=int(repeticiones),
            build_ms_prom=float(statistics.fmean(build_heap)),
            query_ms_prom=float(statistics.fmean(pop_heap)),
            query_ms_mediana=float(statistics.median(pop_heap)),
            extra="query_ms_* representa heappop() repetido n veces",
        )
    )

    return filas


def _print_table(filas: list[ResultadoFila]) -> None:
    cols = [
        ("experimento", 22),
        ("n", 8),
        ("m", 8),
        ("rep", 6),
        ("build_ms", 12),
        ("query_ms_prom", 14),
        ("query_ms_med", 14),
    ]

    def fmt_row(r: ResultadoFila) -> list[str]:
        return [
            r.experimento,
            str(r.n),
            str(r.m),
            str(r.repeticiones),
            f"{r.build_ms_prom:.3f}",
            f"{r.query_ms_prom:.3f}",
            f"{r.query_ms_mediana:.3f}",
        ]

    header = [c for c, _w in cols]
    widths = [w for _c, w in cols]

    def pad(s: str, w: int) -> str:
        if len(s) >= w:
            return s[: w - 1] + "…"
        return s + " " * (w - len(s))

    print("\n" + " ".join(pad(h, w) for h, w in zip(header, widths)))
    print(" ".join("-" * w for w in widths))
    for r in filas:
        row = fmt_row(r)
        print(" ".join(pad(v, w) for v, w in zip(row, widths)))


def _write_csv(filas: list[ResultadoFila], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "experimento",
                "n",
                "m",
                "repeticiones",
                "build_ms_prom",
                "query_ms_prom",
                "query_ms_mediana",
                "extra",
            ]
        )
        for r in filas:
            w.writerow(
                [
                    r.experimento,
                    r.n,
                    r.m,
                    r.repeticiones,
                    f"{r.build_ms_prom:.6f}",
                    f"{r.query_ms_prom:.6f}",
                    f"{r.query_ms_mediana:.6f}",
                    r.extra,
                ]
            )


def main() -> None:
    # Defaults pensados para que corra rápido en laptops.
    semilla = int(os.environ.get("BENCH_SEED", "123"))

    tamanos = [500, 2_000, 10_000]
    m_consultas = 1_000
    rep_vp = 5
    max_coord = 200

    n_avl = 50_000
    rep_avl = 5

    filas: list[ResultadoFila] = []

    print("Benchmark: VP-Tree vs Búsqueda lineal (distancia Manhattan)")
    filas.extend(
        bench_vptree_vs_lineal(
            tamanos=tamanos,
            m_consultas=m_consultas,
            repeticiones=rep_vp,
            semilla=semilla,
            max_coord=max_coord,
        )
    )

    print("\nBenchmark: AVL vs heapq (insertar + extraer mínimos)")
    filas.extend(
        bench_avl_vs_heapq(
            n=n_avl,
            repeticiones=rep_avl,
            semilla=semilla,
        )
    )

    _print_table(filas)

    out_csv = PROYECTO_ROOT / "benchmark_results.csv"
    _write_csv(filas, out_csv)
    print(f"\nCSV guardado en: {out_csv.name}")
    print("Tip: puedes cambiar la semilla con BENCH_SEED=... (variable de entorno).")


if __name__ == "__main__":
    main()
