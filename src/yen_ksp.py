from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from .a_star import Coord, ResultadoAEstrella, a_estrella
from .avl import ArbolAVL


@dataclass(frozen=True)
class Ruta:
    ruta_id: int
    camino: list[Coord]
    distancia_total: int
    tiempo_total: int
    riesgo: int
    costo_total: float


def yen_k_mejores_rutas(
    *,
    filas: int,
    columnas: int,
    inicio: Coord,
    fin: Coord,
    es_bloqueado: Callable[[Coord], bool],
    arista_bloqueada_base: Optional[Callable[[Coord, Coord], bool]] = None,
    tiempo_paso: Callable[[Coord, Coord], float],
    costo_paso: Callable[[Coord, Coord], float],
    riesgo_ruta: Callable[[list[Coord]], int],
    k: int,
) -> list[Ruta]:
    """Yen (K-shortest loopless paths) usando A* como subrutina.

    Devuelve rutas ordenadas por `costo_total` ascendente.
    """

    if k <= 0:
        return []

    r0 = a_estrella(
        filas,
        columnas,
        inicio,
        fin,
        es_bloqueado=es_bloqueado,
        costo_paso=costo_paso,
        arista_bloqueada=arista_bloqueada_base,
    )
    if r0 is None:
        return []

    def empaquetar(ruta_id: int, camino: list[Coord], costo_total: float) -> Ruta:
        dist = max(0, len(camino) - 1)
        tiempo_total = 0.0
        for a, b in zip(camino[:-1], camino[1:]):
            tiempo_total += float(tiempo_paso(a, b))
        riesgo = riesgo_ruta(camino)
        return Ruta(
            ruta_id=ruta_id,
            camino=camino,
            distancia_total=dist,
            tiempo_total=int(round(tiempo_total)),
            riesgo=riesgo,
            costo_total=float(costo_total),
        )

    A: list[tuple[list[Coord], float]] = [(r0.camino, r0.costo_total)]

    # B como AVL: clave=costo_total, valor=camino (tuple)
    B = ArbolAVL[float, tuple[Coord, ...]]()
    en_B: set[tuple[Coord, ...]] = set()

    for i in range(k - 1):
        camino_i, _costo_i = A[i]

        for j in range(len(camino_i) - 1):
            spur = camino_i[j]
            raiz = camino_i[: j + 1]

            # Bloquear nodos del prefijo (excepto spur) para evitar ciclos
            nodos_bloqueados = set(raiz[:-1])

            # Bloquear aristas que harían repetir rutas previas con mismo prefijo
            aristas_bloqueadas: set[tuple[Coord, Coord]] = set()
            for p_camino, _p_cost in A:
                if len(p_camino) > j and p_camino[: j + 1] == raiz:
                    aristas_bloqueadas.add((p_camino[j], p_camino[j + 1]))

            def arista_bloq(u: Coord, v: Coord) -> bool:
                if arista_bloqueada_base and arista_bloqueada_base(u, v):
                    return True
                return (u, v) in aristas_bloqueadas

            def nodo_bloq(n: Coord) -> bool:
                return n in nodos_bloqueados

            spur_res: Optional[ResultadoAEstrella] = a_estrella(
                filas,
                columnas,
                spur,
                fin,
                es_bloqueado=es_bloqueado,
                costo_paso=costo_paso,
                arista_bloqueada=arista_bloq,
                nodo_bloqueado=nodo_bloq,
            )

            if spur_res is None:
                continue

            nuevo_camino = raiz[:-1] + spur_res.camino
            t = tuple(nuevo_camino)
            if t in en_B:
                continue

            # Costo del camino completo = costo(raíz) + costo(spur)
            costo_raiz = 0.0
            for a, b in zip(raiz[:-1], raiz[1:]):
                costo_raiz += float(costo_paso(a, b))

            costo_total = costo_raiz + float(spur_res.costo_total)

            B.insertar(float(costo_total), t)
            en_B.add(t)

        if B.esta_vacio():
            break

        costo_min, camino_min_t = B.extraer_minimo()
        en_B.remove(camino_min_t)
        A.append((list(camino_min_t), float(costo_min)))

    rutas: list[Ruta] = []
    for idx, (camino, costo_total) in enumerate(A[:k], start=1):
        rutas.append(empaquetar(idx, camino, costo_total))

    rutas.sort(key=lambda r: r.costo_total)
    # Reasignar IDs en orden mostrado
    rutas = [Ruta(
        ruta_id=i,
        camino=r.camino,
        distancia_total=r.distancia_total,
        tiempo_total=r.tiempo_total,
        riesgo=r.riesgo,
        costo_total=r.costo_total,
    ) for i, r in enumerate(rutas, start=1)]

    return rutas
