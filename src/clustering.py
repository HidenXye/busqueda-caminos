from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Zona:
    zona_id: int
    puntos: list[tuple[int, int]]

    @property
    def tamano(self) -> int:
        return len(self.puntos)

    def centroide(self) -> tuple[float, float]:
        if not self.puntos:
            return 0.0, 0.0
        sx = sum(p[0] for p in self.puntos)
        sy = sum(p[1] for p in self.puntos)
        n = len(self.puntos)
        return sx / n, sy / n

    def bbox(self) -> tuple[int, int, int, int]:
        """(min_x, min_y, max_x, max_y)"""
        xs = [p[0] for p in self.puntos]
        ys = [p[1] for p in self.puntos]
        return min(xs), min(ys), max(xs), max(ys)


def clusterizar_puntos_manhattan(
    puntos: list[tuple[int, int]],
    *,
    radio: int = 1,
    tamano_minimo: int = 6,
) -> list[Zona]:
    """Clustering simple por conectividad (Manhattan) en una grilla.

    - Une puntos si están a distancia Manhattan <= radio.
    - Forma componentes conexas (BFS) y devuelve solo las de tamaño >= tamano_minimo.

    Nota: está pensado para puntos enteros (ej. midpoints de calles bloqueadas).
    """

    if not puntos:
        return []

    radio = max(0, int(radio))
    tamano_minimo = max(1, int(tamano_minimo))

    # Índice para vecindad por hashing en grilla
    s = set(puntos)
    visitado: set[tuple[int, int]] = set()
    zonas: list[Zona] = []
    zona_id = 1

    # Vecinos dentro del radio (Manhattan)
    offsets: list[tuple[int, int]] = []
    for dx in range(-radio, radio + 1):
        for dy in range(-radio, radio + 1):
            if abs(dx) + abs(dy) <= radio:
                offsets.append((dx, dy))

    for p in puntos:
        if p in visitado:
            continue
        if p not in s:
            continue

        cola = [p]
        visitado.add(p)
        comp: list[tuple[int, int]] = []

        while cola:
            x, y = cola.pop()
            comp.append((x, y))
            for dx, dy in offsets:
                q = (x + dx, y + dy)
                if q in s and q not in visitado:
                    visitado.add(q)
                    cola.append(q)

        if len(comp) >= tamano_minimo:
            zonas.append(Zona(zona_id=zona_id, puntos=comp))
            zona_id += 1

    # Ordenar por tamaño desc (zonas más densas primero)
    zonas.sort(key=lambda z: z.tamano, reverse=True)
    # Reasignar IDs en orden
    zonas = [Zona(zona_id=i, puntos=z.puntos) for i, z in enumerate(zonas, start=1)]
    return zonas
