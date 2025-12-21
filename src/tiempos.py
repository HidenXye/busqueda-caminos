from __future__ import annotations

import random

from .grid import Arista, ConfigMapa, calles_del_mapa


def generar_tiempos_calles(
    *,
    conf: ConfigMapa,
    semilla: int,
    tiempo_min: int = 1,
    tiempo_max: int = 5,
) -> dict[Arista, int]:
    """Asigna un tiempo de cruce (peso) a cada calle del mapa.

    - Determinista por `semilla` (reproducible).
    - Los tiempos son enteros en [tiempo_min, tiempo_max].

    Nota: los obstáculos se manejan aparte como calles bloqueadas.
    """

    tmin = max(1, int(tiempo_min))
    tmax = max(tmin, int(tiempo_max))

    rng = random.Random(int(semilla))
    tiempos: dict[Arista, int] = {}
    for a in calles_del_mapa(conf):
        tiempos[a] = rng.randint(tmin, tmax)
    return tiempos
