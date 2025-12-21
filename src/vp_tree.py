from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Optional, Sequence, TypeVar

P = TypeVar("P")


def distancia_manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


@dataclass
class _NodoVPTree(Generic[P]):
    punto: P
    radio: int
    dentro: Optional["_NodoVPTree[P]"]
    fuera: Optional["_NodoVPTree[P]"]


class ArbolProximidadVP(Generic[P]):
    """Árbol de proximidad basado en distancia (VP-Tree).

    Se usa para consultas de cercanía: encontrar el obstáculo más cercano a un punto.
    """

    def __init__(self, puntos: Sequence[P], distancia: Callable[[P, P], int]):
        self._distancia = distancia
        self._raiz = self._construir(list(puntos))

    def _construir(self, puntos: list[P]) -> Optional[_NodoVPTree[P]]:
        if not puntos:
            return None

        vp = puntos.pop()  # punto de vista
        if not puntos:
            return _NodoVPTree(punto=vp, radio=0, dentro=None, fuera=None)

        distancias = [(self._distancia(vp, p), p) for p in puntos]
        distancias.sort(key=lambda x: x[0])
        med = len(distancias) // 2
        radio = distancias[med][0]

        dentro_pts = [p for d, p in distancias if d <= radio]
        fuera_pts = [p for d, p in distancias if d > radio]

        return _NodoVPTree(
            punto=vp,
            radio=radio,
            dentro=self._construir(dentro_pts),
            fuera=self._construir(fuera_pts),
        )

    def mas_cercano(self, objetivo: P) -> tuple[Optional[P], int]:
        """Retorna (punto_mas_cercano, distancia)."""
        if self._raiz is None:
            return None, 10**9

        mejor_punto: Optional[P] = None
        mejor_dist = 10**9

        def buscar(nodo: Optional[_NodoVPTree[P]]) -> None:
            nonlocal mejor_punto, mejor_dist
            if nodo is None:
                return

            d = self._distancia(objetivo, nodo.punto)
            if d < mejor_dist:
                mejor_dist = d
                mejor_punto = nodo.punto

            if nodo.dentro is None and nodo.fuera is None:
                return

            # Decidir orden de búsqueda según la relación con el radio
            if d <= nodo.radio:
                buscar(nodo.dentro)
                if d + mejor_dist > nodo.radio:
                    buscar(nodo.fuera)
            else:
                buscar(nodo.fuera)
                if d - mejor_dist <= nodo.radio:
                    buscar(nodo.dentro)

        buscar(self._raiz)
        return mejor_punto, mejor_dist
