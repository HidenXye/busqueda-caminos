from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Callable, Iterable, Optional

Coord = tuple[int, int]


def vecinos_4(filas: int, columnas: int, nodo: Coord) -> Iterable[Coord]:
    f, c = nodo
    if f > 0:
        yield (f - 1, c)
    if f < filas - 1:
        yield (f + 1, c)
    if c > 0:
        yield (f, c - 1)
    if c < columnas - 1:
        yield (f, c + 1)


def heuristica_manhattan(a: Coord, b: Coord) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


@dataclass(frozen=True)
class ResultadoAEstrella:
    camino: list[Coord]
    costo_total: float


def a_estrella(
    filas: int,
    columnas: int,
    inicio: Coord,
    fin: Coord,
    es_bloqueado: Callable[[Coord], bool],
    costo_paso: Callable[[Coord, Coord], float],
    arista_bloqueada: Optional[Callable[[Coord, Coord], bool]] = None,
    nodo_bloqueado: Optional[Callable[[Coord], bool]] = None,
) -> Optional[ResultadoAEstrella]:
    """A* con movimiento 4-direcciones.

    `costo_paso(u, v)` debe ser >= 1 para mantener heurística (Manhattan) admisible.
    """

    if inicio == fin:
        return ResultadoAEstrella(camino=[inicio], costo_total=0.0)
    if es_bloqueado(inicio) or es_bloqueado(fin):
        return None

    def permitido(n: Coord) -> bool:
        if es_bloqueado(n):
            return False
        if nodo_bloqueado and nodo_bloqueado(n):
            return False
        return True

    if not permitido(inicio) or not permitido(fin):
        return None

    abiertos: list[tuple[float, float, Coord]] = []
    g: dict[Coord, float] = {inicio: 0.0}
    padre: dict[Coord, Coord] = {}

    f0 = heuristica_manhattan(inicio, fin)
    heapq.heappush(abiertos, (f0, 0.0, inicio))

    visitado: set[Coord] = set()

    while abiertos:
        _, g_actual, actual = heapq.heappop(abiertos)
        if actual in visitado:
            continue
        visitado.add(actual)

        if actual == fin:
            camino: list[Coord] = [fin]
            while camino[-1] != inicio:
                camino.append(padre[camino[-1]])
            camino.reverse()
            return ResultadoAEstrella(camino=camino, costo_total=g[fin])

        for v in vecinos_4(filas, columnas, actual):
            if not permitido(v):
                continue
            if arista_bloqueada and arista_bloqueada(actual, v):
                continue

            tentativo = g_actual + float(costo_paso(actual, v))
            if tentativo < g.get(v, 10**18):
                g[v] = tentativo
                padre[v] = actual
                f = tentativo + heuristica_manhattan(v, fin)
                heapq.heappush(abiertos, (f, tentativo, v))

    return None
