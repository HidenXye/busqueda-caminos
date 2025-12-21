from __future__ import annotations

import random
from dataclasses import dataclass

Coord = tuple[int, int]
Arista = tuple[Coord, Coord]


@dataclass(frozen=True)
class ConfigMapa:
    filas: int
    columnas: int


def dentro_del_mapa(conf: ConfigMapa, p: Coord) -> bool:
    f, c = p
    return 0 <= f < conf.filas and 0 <= c < conf.columnas


def normalizar_arista(a: Coord, b: Coord) -> Arista:
    """Normaliza una arista no dirigida (a,b) para usarla en sets/dicts."""
    return (a, b) if a <= b else (b, a)


def calles_del_mapa(conf: ConfigMapa) -> list[Arista]:
    """Lista todas las calles (aristas) posibles entre intersecciones vecinas."""
    aristas: list[Arista] = []
    for f in range(conf.filas):
        for c in range(conf.columnas):
            u = (f, c)
            if c + 1 < conf.columnas:
                aristas.append(normalizar_arista(u, (f, c + 1)))
            if f + 1 < conf.filas:
                aristas.append(normalizar_arista(u, (f + 1, c)))
    return aristas


def generar_obstaculos(
    *,
    conf: ConfigMapa,
    densidad_obstaculos: float,
    semilla: int,
    inicio: Coord,
    fin: Coord,
    max_intentos: int = 20,
    hay_solucion: callable,
) -> set[Arista]:
    """Genera obstáculos como *calles bloqueadas* (aristas) con densidad dada.

    Regla (interpretación práctica): inicio y fin son intersecciones válidas; los obstáculos bloquean calles.
    Intenta hasta `max_intentos` que exista solución (según `hay_solucion`).
    """

    dens = float(densidad_obstaculos)
    dens = max(0.0, min(1.0, dens))

    todas = calles_del_mapa(conf)
    total = len(todas)
    objetivo = int(round(dens * total))

    for intento in range(max_intentos):
        rng = random.Random(int(semilla) + intento)
        candidatas = list(todas)
        rng.shuffle(candidatas)
        obs = set(candidatas[: min(objetivo, len(candidatas))])

        if hay_solucion(obs):
            return obs

    # Último intento: devuelve aunque no haya solución (la UI permite regenerar)
    rng = random.Random(int(semilla))
    candidatas = list(todas)
    rng.shuffle(candidatas)
    return set(candidatas[: min(objetivo, len(candidatas))])
