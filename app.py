from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.a_star import a_estrella
from src.grid import (
    Arista,
    ConfigMapa,
    dentro_del_mapa,
    generar_obstaculos,
    normalizar_arista,
)
from src.exportar import exportar_resultados_csv
from src.tiempos import generar_tiempos_calles
from src.vp_tree import ArbolProximidadVP, distancia_manhattan
from src.yen_ksp import Ruta, yen_k_mejores_rutas


def _renderizar_mapa_html(
    *,
    conf: ConfigMapa,
    obstaculos: set[Arista],
    tiempos_calles: dict[Arista, int],
    inicio: tuple[int, int],
    fin: tuple[int, int],
    camino: list[tuple[int, int]] | None,
) -> str:
    # Mapa estilo "calles": intersecciones + segmentos. Render en SVG responsive.
    color_fondo = "#f7f8fb"
    color_manzana = "#eef0f6"
    color_borde_manzana = "#e2e5ee"

    color_calle_borde = "#b6bcc8"
    color_calle_centro = "#dfe3ec"
    color_obstaculo = "#e53935"  # calle bloqueada
    color_inicio = "#2ecc71"
    color_fin = "#f1c40f"
    color_ruta = "#2d6cdf"
    color_etiqueta_fondo = "#ffffff"
    color_etiqueta_borde = "#cbd5e1"
    color_etiqueta_texto = "#334155"

    # Escalado: intenta verse grande en pantalla, pero sin explotar en grids grandes.
    max_dim = max(conf.filas - 1, conf.columnas - 1)
    sep = int(max(14, min(52, 920 / max(1, max_dim))))
    pad = int(max(18, sep * 0.8))
    w = pad * 2 + (conf.columnas - 1) * sep
    h = pad * 2 + (conf.filas - 1) * sep

    def xy(p: tuple[int, int]) -> tuple[int, int]:
        f, c = p
        return pad + c * sep, pad + f * sep

    def xy_expandido(p: tuple[float, float]) -> tuple[float, float]:
        # p está en coordenadas "expandida" (2x). Convertir a coordenadas de intersección (dividir entre 2).
        fx = float(p[0]) / 2.0
        cx = float(p[1]) / 2.0
        return float(pad) + cx * float(sep), float(pad) + fx * float(sep)

    ruta_seg = set()
    if camino and len(camino) >= 2:
        for a, b in zip(camino[:-1], camino[1:]):
            ruta_seg.add(normalizar_arista(a, b))

    # Manzanas (cuadras) de fondo: rectángulos entre intersecciones
    manzanas = []
    if conf.filas >= 2 and conf.columnas >= 2:
        for f in range(conf.filas - 1):
            for c in range(conf.columnas - 1):
                x, y = xy((f, c))
                # Rectángulo centrado en el espacio entre calles
                bx = x + int(sep * 0.18)
                by = y + int(sep * 0.18)
                bw = int(sep * 0.64)
                bh = int(sep * 0.64)
                manzanas.append(
                    f"<rect x='{bx}' y='{by}' width='{bw}' height='{bh}' rx='{int(sep*0.12)}' ry='{int(sep*0.12)}' fill='{color_manzana}' stroke='{color_borde_manzana}' stroke-width='1' />"
                )

    # Dibujar calles base (doble trazo: borde + centro)
    calles_borde = []
    calles_centro = []
    obst_lineas = []
    ruta_lineas = []
    etiquetas_calles = []
    for f in range(conf.filas):
        for c in range(conf.columnas):
            u = (f, c)
            x1, y1 = xy(u)
            if c + 1 < conf.columnas:
                v = (f, c + 1)
                x2, y2 = xy(v)
                a = normalizar_arista(u, v)
                if a in obstaculos:
                    obst_lineas.append(
                        f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='{color_obstaculo}' stroke-width='{max(6, int(sep*0.16))}' stroke-linecap='round' />"
                    )
                elif a in ruta_seg:
                    ruta_lineas.append(
                        f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='{color_ruta}' stroke-width='{max(6, int(sep*0.16))}' stroke-linecap='round' />"
                    )
                else:
                    sw_b = max(6, int(sep * 0.18))
                    sw_c = max(3, int(sep * 0.10))
                    calles_borde.append(
                        f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='{color_calle_borde}' stroke-width='{sw_b}' stroke-linecap='round' />"
                    )
                    calles_centro.append(
                        f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='{color_calle_centro}' stroke-width='{sw_c}' stroke-linecap='round' />"
                    )

                # Etiqueta con tiempo de cruce (para entender el costo por calle)
                if a not in obstaculos:
                    t = int(tiempos_calles.get(a, 1))
                    mx = (x1 + x2) / 2.0
                    my = (y1 + y2) / 2.0
                    txt = str(t)
                    # Fondo simple para legibilidad (tamaño aproximado por cantidad de dígitos)
                    wtxt = 10 + 7 * max(1, len(txt))
                    htxt = 16
                    etiquetas_calles.append(
                        f"<rect x='{mx - wtxt/2:.1f}' y='{my - htxt/2:.1f}' width='{wtxt}' height='{htxt}' rx='4' ry='4' fill='{color_etiqueta_fondo}' fill-opacity='0.85' stroke='{color_etiqueta_borde}' stroke-width='1' />"
                    )
                    etiquetas_calles.append(
                        f"<text x='{mx:.1f}' y='{my + 4:.1f}' text-anchor='middle' font-size='{max(10, int(sep*0.20))}' fill='{color_etiqueta_texto}' font-family='system-ui, -apple-system, Segoe UI, Roboto, Arial'>"
                        f"{txt}</text>"
                    )
            if f + 1 < conf.filas:
                v = (f + 1, c)
                x2, y2 = xy(v)
                a = normalizar_arista(u, v)
                if a in obstaculos:
                    obst_lineas.append(
                        f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='{color_obstaculo}' stroke-width='{max(6, int(sep*0.16))}' stroke-linecap='round' />"
                    )
                elif a in ruta_seg:
                    ruta_lineas.append(
                        f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='{color_ruta}' stroke-width='{max(6, int(sep*0.16))}' stroke-linecap='round' />"
                    )
                else:
                    sw_b = max(6, int(sep * 0.18))
                    sw_c = max(3, int(sep * 0.10))
                    calles_borde.append(
                        f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='{color_calle_borde}' stroke-width='{sw_b}' stroke-linecap='round' />"
                    )
                    calles_centro.append(
                        f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='{color_calle_centro}' stroke-width='{sw_c}' stroke-linecap='round' />"
                    )

                # Etiqueta con tiempo de cruce
                if a not in obstaculos:
                    t = int(tiempos_calles.get(a, 1))
                    mx = (x1 + x2) / 2.0
                    my = (y1 + y2) / 2.0
                    txt = str(t)
                    wtxt = 10 + 7 * max(1, len(txt))
                    htxt = 16
                    etiquetas_calles.append(
                        f"<rect x='{mx - wtxt/2:.1f}' y='{my - htxt/2:.1f}' width='{wtxt}' height='{htxt}' rx='4' ry='4' fill='{color_etiqueta_fondo}' fill-opacity='0.85' stroke='{color_etiqueta_borde}' stroke-width='1' />"
                    )
                    etiquetas_calles.append(
                        f"<text x='{mx:.1f}' y='{my + 4:.1f}' text-anchor='middle' font-size='{max(10, int(sep*0.20))}' fill='{color_etiqueta_texto}' font-family='system-ui, -apple-system, Segoe UI, Roboto, Arial'>"
                        f"{txt}</text>"
                    )

    # Intersecciones
    nodos = []
    for f in range(conf.filas):
        for c in range(conf.columnas):
            p = (f, c)
            x, y = xy(p)
            fill = "#ffffff"
            r = max(3, int(sep * 0.10))
            if p == inicio:
                fill = color_inicio
                r = max(7, int(sep * 0.18))
            elif p == fin:
                fill = color_fin
                r = max(7, int(sep * 0.18))
            nodos.append(
                f"<circle cx='{x}' cy='{y}' r='{r}' fill='{fill}' stroke='#6b7280' stroke-width='1' />"
            )

    leyenda = (
        "<div style='display:flex;gap:12px;flex-wrap:wrap;margin:6px 0 10px 0;'>"
        f"<div><span style='display:inline-block;width:18px;height:6px;background:{color_obstaculo};'></span> calle bloqueada</div>"
        f"<div><span style='display:inline-block;width:18px;height:6px;background:{color_ruta};'></span> ruta</div>"
        f"<div><span style='display:inline-block;width:12px;height:12px;background:{color_inicio};border:1px solid #666;'></span> inicio</div>"
        f"<div><span style='display:inline-block;width:12px;height:12px;background:{color_fin};border:1px solid #666;'></span> fin</div>"
        "</div>"
    )

    svg = (
        f"<svg viewBox='0 0 {w} {h}' preserveAspectRatio='xMinYMin meet' "
        f"style='width:100%;height:auto;max-width:1100px;background:{color_fondo};border:1px solid #e6e6e6;border-radius:10px;'>"
        + "".join(manzanas)
        + "".join(calles_borde)
        + "".join(calles_centro)
        + "".join(obst_lineas)
        + "".join(ruta_lineas)
        + "".join(etiquetas_calles)
        + "".join(nodos)
        + "</svg>"
    )
    return f"{leyenda}{svg}"


def _validar_coord(conf: ConfigMapa, fila: int, col: int) -> tuple[bool, str]:
    if not dentro_del_mapa(conf, (fila, col)):
        return False, "La coordenada está fuera del mapa. Recuerda: índices desde 0."
    return True, ""


def main() -> None:
    st.set_page_config(page_title="Rutas óptimas (prototipo)", layout="wide")
    st.markdown(
        "<h1 style='text-align:center;margin-bottom:0.25rem;'>"
        "Cálculo de K rutas cortas con obstáculos en calles"
        "</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;color:#6b7280;margin-top:0;'>"
        "Coordenadas enteras (fila, columna) empezando en 0. Movimiento permitido: arriba/abajo/izquierda/derecha."
        "</p>",
        unsafe_allow_html=True,
    )

    if "conf" not in st.session_state:
        st.session_state.conf = ConfigMapa(filas=10, columnas=14)
    if "inicio" not in st.session_state:
        st.session_state.inicio = (0, 0)
    if "fin" not in st.session_state:
        st.session_state.fin = (9, 13)
    if "obstaculos" not in st.session_state:
        st.session_state.obstaculos = set()
    if "vp" not in st.session_state:
        st.session_state.vp = ArbolProximidadVP([], distancia=distancia_manhattan)
    if "rutas" not in st.session_state:
        st.session_state.rutas = []
    if "ruta_seleccionada" not in st.session_state:
        st.session_state.ruta_seleccionada = 1
    if "ruta_idx" not in st.session_state:
        st.session_state.ruta_idx = 0
    if "tiempos_calles" not in st.session_state:
        st.session_state.tiempos_calles = {}

    # --- Controles (arriba) ---
    c_mapa, c_vehiculo = st.columns([1.1, 1.3])

    with c_mapa:
        st.subheader("Mapa")
        filas = st.number_input("Filas", min_value=2, max_value=60, value=int(st.session_state.conf.filas), step=1)
        columnas = st.number_input("Columnas", min_value=2, max_value=60, value=int(st.session_state.conf.columnas), step=1)
        densidad = st.slider("Densidad de obstáculos", min_value=0.0, max_value=0.8, value=0.20, step=0.01)
        semilla = st.number_input("Semilla (int)", value=123, step=1)

        st.markdown("**Tiempos de cruce por calle (aleatorio)**")
        tiempo_min = st.number_input("Tiempo mínimo por calle", min_value=1, max_value=60, value=1, step=1)
        tiempo_max = st.number_input("Tiempo máximo por calle", min_value=1, max_value=60, value=5, step=1)

        if st.button("Generar obstáculos", type="secondary"):
            st.session_state.conf = ConfigMapa(filas=int(filas), columnas=int(columnas))

            # Generar tiempos de cruce reproducibles (pesos por calle)
            st.session_state.tiempos_calles = generar_tiempos_calles(
                conf=st.session_state.conf,
                semilla=int(semilla) + 10_000,
                tiempo_min=int(tiempo_min),
                tiempo_max=int(tiempo_max),
            )

            def arista_bloqueada_desde(obs: set[Arista]):
                def f(u: tuple[int, int], v: tuple[int, int]) -> bool:
                    return normalizar_arista(u, v) in obs

                return f

            def hay_solucion(obs: set[Arista]) -> bool:
                conf = st.session_state.conf
                inicio = st.session_state.inicio
                fin = st.session_state.fin
                res = a_estrella(
                    conf.filas,
                    conf.columnas,
                    inicio,
                    fin,
                    es_bloqueado=lambda _p: False,
                    costo_paso=lambda _u, _v: 1.0,
                    arista_bloqueada=arista_bloqueada_desde(obs),
                )
                return res is not None

            obs = generar_obstaculos(
                conf=st.session_state.conf,
                densidad_obstaculos=float(densidad),
                semilla=int(semilla),
                inicio=st.session_state.inicio,
                fin=st.session_state.fin,
                hay_solucion=hay_solucion,
            )
            st.session_state.obstaculos = obs

            # Indexar obstáculos en calles como puntos (midpoints) en una rejilla expandida (2x)
            puntos: list[tuple[int, int]] = []
            for u, v in obs:
                (f1, c1), (f2, c2) = u, v
                x1, y1 = 2 * f1, 2 * c1
                x2, y2 = 2 * f2, 2 * c2
                puntos.append(((x1 + x2) // 2, (y1 + y2) // 2))

            st.session_state.vp = ArbolProximidadVP(puntos, distancia=distancia_manhattan)
            st.session_state.rutas = []
            st.session_state.ruta_seleccionada = 1

    with c_vehiculo:
        st.subheader("Vehículo (solo 1)")
        conf = st.session_state.conf

        st.markdown("**Inicio**")
        ini_f = st.number_input("inicio_fila", value=int(st.session_state.inicio[0]), step=1)
        ini_c = st.number_input("inicio_columna", value=int(st.session_state.inicio[1]), step=1)

        st.markdown("**Fin**")
        fin_f = st.number_input("fin_fila", value=int(st.session_state.fin[0]), step=1)
        fin_c = st.number_input("fin_columna", value=int(st.session_state.fin[1]), step=1)

        k = st.number_input("K (top‑K rutas)", min_value=1, max_value=30, value=5, step=1)

        criterio = st.radio(
            "Criterio de decisión",
            options=["Minimizar distancia (pasos)", "Minimizar tiempo (ETA)"],
            index=0,
        )

        if st.button("Calcular rutas", type="primary"):
            st.session_state.conf = ConfigMapa(filas=int(filas), columnas=int(columnas))
            conf = st.session_state.conf

            ok, msg = _validar_coord(conf, int(ini_f), int(ini_c))
            if not ok:
                st.error(msg)
                st.stop()
            ok, msg = _validar_coord(conf, int(fin_f), int(fin_c))
            if not ok:
                st.error(msg)
                st.stop()

            inicio = (int(ini_f), int(ini_c))
            fin = (int(fin_f), int(fin_c))

            if inicio == fin:
                st.warning("Inicio y fin son iguales; la ruta tiene 0 pasos.")

            obstaculos: set[Arista] = st.session_state.obstaculos
            tiempos_calles: dict[Arista, int] = st.session_state.tiempos_calles

            if not tiempos_calles:
                # Caso: el usuario no presionó "Generar obstáculos" antes.
                tiempos_calles = generar_tiempos_calles(
                    conf=conf,
                    semilla=int(semilla) + 10_000,
                    tiempo_min=1,
                    tiempo_max=5,
                )
                st.session_state.tiempos_calles = tiempos_calles

            def arista_bloqueada(u: tuple[int, int], v: tuple[int, int]) -> bool:
                return normalizar_arista(u, v) in obstaculos

            st.session_state.inicio = inicio
            st.session_state.fin = fin

            vp: ArbolProximidadVP[tuple[int, int]] = st.session_state.vp

            def a_expandido(p: tuple[int, int]) -> tuple[int, int]:
                return (2 * p[0], 2 * p[1])

            def dist_a_obstaculo(p: tuple[int, int]) -> int:
                _q, d = vp.mas_cercano(a_expandido(p))
                return int(d)

            def costo_paso(u: tuple[int, int], v: tuple[int, int]) -> float:
                if criterio == "Minimizar distancia (pasos)":
                    return 1.0
                # Minimizar tiempo (ETA): costo = tiempo de cruce de la calle
                return float(tiempos_calles.get(normalizar_arista(u, v), 1))

            def tiempo_paso(u: tuple[int, int], v: tuple[int, int]) -> float:
                return float(tiempos_calles.get(normalizar_arista(u, v), 1))

            def riesgo_ruta(camino: list[tuple[int, int]]) -> int:
                if not obstaculos:
                    return conf.filas + conf.columnas
                return min(dist_a_obstaculo(p) for p in camino)

            rutas = yen_k_mejores_rutas(
                filas=conf.filas,
                columnas=conf.columnas,
                inicio=inicio,
                fin=fin,
                es_bloqueado=lambda _p: False,
                arista_bloqueada_base=arista_bloqueada,
                tiempo_paso=tiempo_paso,
                costo_paso=costo_paso,
                riesgo_ruta=riesgo_ruta,
                k=int(k),
            )

            st.session_state.rutas = rutas
            st.session_state.ruta_seleccionada = 1

            if not rutas:
                st.warning(
                    "No se encontraron rutas con los obstáculos actuales. Puedes regenerar obstáculos o cambiar inicio/fin."
                )
            else:
                ruta_csv = Path(__file__).parent / "results.csv"
                exportar_resultados_csv(rutas, ruta_csv)
                st.success(f"Se calcularon {len(rutas)} rutas. Exportado: {ruta_csv.name}")

    st.divider()

    # --- Visualización (abajo) ---
    col_mapa, col_panel = st.columns([2.2, 1.2], vertical_alignment="top")

    with col_panel:
        st.subheader("Mapa y rutas")
        conf = st.session_state.conf
        inicio = st.session_state.inicio
        fin = st.session_state.fin
        obstaculos = st.session_state.obstaculos
        rutas: list[Ruta] = st.session_state.rutas

        ruta_sel: Ruta | None = None
        if rutas:
            opciones = [f"Ruta {r.ruta_id} (costo={r.costo_total:.3f})" for r in rutas]
            idx = st.selectbox(
                "Selecciona una ruta",
                options=list(range(len(opciones))),
                format_func=lambda i: opciones[i],
                index=min(int(st.session_state.ruta_idx), max(0, len(opciones) - 1)),
            )
            st.session_state.ruta_idx = int(idx)
            ruta_sel = rutas[int(idx)]
            st.markdown(
                "**Componentes:** distancia = pasos, tiempo (ETA) = suma de tiempos de cruce por calle, riesgo = distancia mínima a calle bloqueada."
            )
            st.write(
                {
                    "ruta_id": ruta_sel.ruta_id,
                    "distancia_total": ruta_sel.distancia_total,
                    "tiempo_total (ETA)": ruta_sel.tiempo_total,
                    "riesgo (distancia mínima)": ruta_sel.riesgo,
                    "costo_total": float(f"{ruta_sel.costo_total:.6f}"),
                }
            )
        else:
            st.info("Genera obstáculos y luego calcula rutas para ver alternativas.")

        st.markdown(
            "**Algoritmos:** A* (base) + Yen (top‑K sin ciclos).\n\n"
            "**Árboles:** AVL (ordenar candidatos) + VP‑Tree (proximidad/riesgo)."
        )

    with col_mapa:
        conf = st.session_state.conf
        inicio = st.session_state.inicio
        fin = st.session_state.fin
        obstaculos = st.session_state.obstaculos
        tiempos_calles: dict[Arista, int] = st.session_state.tiempos_calles
        rutas: list[Ruta] = st.session_state.rutas

        camino = None
        if rutas:
            idx = min(int(st.session_state.ruta_idx), max(0, len(rutas) - 1))
            camino = rutas[idx].camino
        html = _renderizar_mapa_html(
            conf=conf,
            obstaculos=obstaculos,
            tiempos_calles=tiempos_calles,
            inicio=inicio,
            fin=fin,
            camino=camino,
        )
        st.markdown(html, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
