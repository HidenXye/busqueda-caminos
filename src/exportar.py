from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .yen_ksp import Ruta


def exportar_resultados_csv(rutas: Iterable[Ruta], ruta_archivo: Path) -> None:
    ruta_archivo.parent.mkdir(parents=True, exist_ok=True)
    with ruta_archivo.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "ruta_id",
                "distancia_total",
                "tiempo_total",
                "riesgo",
                "costo_total",
            ],
        )
        writer.writeheader()
        for r in rutas:
            writer.writerow(
                {
                    "ruta_id": r.ruta_id,
                    "distancia_total": r.distancia_total,
                    "tiempo_total": r.tiempo_total,
                    "riesgo": r.riesgo,
                    "costo_total": f"{r.costo_total:.6f}",
                }
            )
