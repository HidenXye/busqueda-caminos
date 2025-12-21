# Rutas óptimas en un mapa de calles (Streamlit + Python)

App web local (Streamlit) para calcular y comparar **K rutas** entre un **inicio** y un **fin** sobre un mapa tipo ciudad (intersecciones + calles). Los **obstáculos** se modelan como **calles bloqueadas** (aristas bloqueadas).

El sistema permite elegir el criterio de decisión:
- **Minimizar distancia (pasos)**
- **Minimizar tiempo (ETA)** usando un **tiempo de cruce por calle** (peso/valor visible en el mapa)

Además, reporta un **riesgo** (proximidad a obstáculos) como métrica informativa.

## Ejecutar

### Requisitos
- Python (recomendado 3.10+)

### Instalación

```bash
pip install -r requirements.txt
```

### Levantar la app

```bash
streamlit run app.py
```

Si el puerto por defecto está ocupado:

```bash
streamlit run app.py --server.port 8502
```

## Uso (flujo en la interfaz)

1. En **Mapa** configura:
   - `Filas`, `Columnas`
   - `Densidad de obstáculos`
   - `Semilla`
   - `Tiempo mínimo por calle` y `Tiempo máximo por calle`
2. Clic en **Generar obstáculos**.
   - Genera (a) calles bloqueadas y (b) tiempos por calle reproducibles por semilla.
3. En **Vehículo** configura:
   - Inicio y fin (`inicio_fila/columna`, `fin_fila/columna`)
   - `K` (cantidad de rutas)
   - Criterio (distancia o tiempo)
4. Clic en **Calcular rutas**.
5. En **Mapa y rutas**, selecciona una ruta y observa:
   - el trazado en azul
   - los obstáculos en rojo
   - el número en cada calle (tiempo de cruce) para entender por qué una ruta “gana” en ETA.

## Modelo de datos (qué representa cada cosa)

### Intersecciones y calles
- Una coordenada `(fila, columna)` es una **intersección**.
- Una **calle** es una arista entre intersecciones vecinas (4 direcciones, sin diagonales).

En código, las calles se representan como `Arista = tuple[Coord, Coord]` normalizada con `normalizar_arista(a, b)`.

### Obstáculos
- Un obstáculo es una **calle bloqueada** (una arista que no se puede cruzar).

### Tiempos por calle (pesos)
- Cada calle tiene un entero (por ejemplo 1–5) que representa qué tan rápido/lento es cruzarla.
- Esos valores se dibujan en el mapa (número encima de cada segmento).

## Cálculo paso a paso (qué ocurre internamente)

Esta es la secuencia completa cuando calculas rutas:

### Paso 1) Generar el mapa “navegable”
Archivo: [src/grid.py](src/grid.py)

- `calles_del_mapa(conf)`: enumera todas las aristas posibles del mapa.
- `generar_obstaculos(...)`: elige un subconjunto de calles para bloquear según densidad/semilla.
  - Usa `hay_solucion(obs)` para intentar garantizar que exista camino (reintenta varias veces).

### Paso 2) Asignar tiempo a cada calle
Archivo: [src/tiempos.py](src/tiempos.py)

- `generar_tiempos_calles(conf, semilla, tiempo_min, tiempo_max)`:
  - asigna un entero aleatorio a cada arista.
  - es determinista (misma semilla → mismos tiempos), lo cual ayuda a depurar/explicar.

### Paso 3) Definir el costo por paso según el criterio
Archivo: [app.py](app.py)

Dentro de `main()` se definen:
- `costo_paso(u, v)`:
  - si eliges **distancia** → devuelve `1.0`
  - si eliges **tiempo** → devuelve el tiempo de `normalizar_arista(u, v)`
- `tiempo_paso(u, v)`:
  - siempre devuelve el tiempo de esa calle (se usa para calcular `tiempo_total (ETA)` aunque el criterio sea distancia)

### Paso 4) Calcular la primera ruta óptima con A*
Archivo: [src/a_star.py](src/a_star.py)

- `a_estrella(...)`:
  - explora el grafo 4‑direcciones
  - respeta calles bloqueadas mediante `arista_bloqueada(u, v)`
  - minimiza el acumulado de `costo_paso(u, v)`
  - usa heurística Manhattan (admisible en este grid)

Salida: `ResultadoAEstrella` con `camino` y `costo_total`.

### Paso 5) Generar Top‑K rutas con Yen (sin ciclos)
Archivo: [src/yen_ksp.py](src/yen_ksp.py)

- `yen_k_mejores_rutas(...)` (resumen):
  1. Calcula la ruta óptima inicial `r0` con A*.
  2. Para cada ruta ya aceptada `A[i]`, recorre sus nodos como posibles “spur points”.
  3. Construye rutas candidatas combinando:
     - un prefijo (raíz) + un camino nuevo desde el spur hasta el final.
  4. Evita repetir rutas bloqueando temporalmente ciertas aristas (las que producirían el mismo prefijo que una ruta ya conocida).
  5. Va extrayendo el candidato de menor costo hasta obtener K rutas.

Importante:
- `costo_total` es lo que **Yen minimiza** (distancia o tiempo, según criterio).
- `tiempo_total` se calcula aparte con `tiempo_paso` para reportar ETA real.

### Paso 6) Métricas: distancia, ETA, riesgo, costo

Para cada ruta calculada:
- `distancia_total`: número de aristas del camino (pasos).
- `tiempo_total (ETA)`: suma de `tiempo_paso` por cada arista.
- `costo_total`: suma de `costo_paso` por cada arista.
- `riesgo`: distancia mínima al obstáculo más cercano a lo largo del camino.

### Paso 7) Riesgo (proximidad) con VP‑Tree
Archivo: [src/vp_tree.py](src/vp_tree.py)

- Se construye un VP‑Tree con puntos que representan los obstáculos (midpoints en una rejilla 2x).
- `mas_cercano(p)` devuelve el obstáculo más cercano y su distancia Manhattan.

Nota: hoy el riesgo **no modifica** la ruta (solo se reporta), pero se calcula con el árbol de proximidad como lo pide el proyecto.

### Paso 8) Exportación
Archivo: [src/exportar.py](src/exportar.py)

- `exportar_resultados_csv(rutas, ruta_csv)` escribe/actualiza `results.csv` con:
  - `ruta_id, distancia_total, tiempo_total, riesgo, costo_total`

## Árboles obligatorios (y dónde se usan)

### AVL (árbol balanceado)
Archivo: [src/avl.py](src/avl.py)

- Se usa como “cola de prioridad” dentro de Yen:
  - inserta candidatos con `insertar(clave=costo_total, valor=camino)`
  - extrae el menor con `extraer_minimo()`

### VP‑Tree (proximidad)
Archivo: [src/vp_tree.py](src/vp_tree.py)

- Se usa para responder “¿qué obstáculo queda más cerca?”
- Permite calcular el `riesgo` de cada ruta.

## Render del mapa (qué se ve en pantalla)
Archivo: [app.py](app.py)

- `_renderizar_mapa_html(...)` genera un SVG:
  - calles normales, obstáculos en rojo, ruta en azul
  - números en cada calle = tiempo de cruce (peso)

## Benchmark (rendimiento y eficiencia)

La guía del proyecto pide **analizar rendimiento y eficiencia**. Para eso se incluye un benchmark reproducible que compara:

1) **VP‑Tree vs búsqueda lineal** (nearest neighbour con distancia Manhattan)
- Construcción del VP‑Tree (tiempo de build)
- Tiempo total de **m consultas** de “punto más cercano”
- Validación: el benchmark verifica que VP‑Tree y lineal devuelven las **mismas distancias**

2) **AVL vs `heapq`** (cola de prioridad)
- Inserción de `n` claves
- Extracción de mínimos repetida `n` veces
- Validación: verifica que el orden de salida sea el mismo

### Cómo ejecutar (Windows / PowerShell)

Desde la raíz del proyecto:

```powershell
py -3 .\benchmarks\benchmark.py
```

El script genera:
- una tabla en consola (promedio y mediana)
- un CSV llamado `benchmark_results.csv` en la raíz del proyecto

### Interpretación rápida

- Si `Lineal (consultas)` crece mucho más rápido que `VP-Tree (consultas)` al aumentar `n`, demuestras mejora en consultas de proximidad.
- `build_ms` de VP‑Tree normalmente crece con `n` (trade‑off típico: construir cuesta, consultar se acelera).
- `heapq` es el baseline de Python; comparar contra AVL ayuda a justificar que tu AVL está bien implementado y es utilizable.

### Resultados (ejecución de ejemplo)

Ejecutado en este workspace con **Python 3.12 (Windows)**. Los tiempos varían según la máquina, pero la tendencia es lo importante.

```text
experimento            n        m        rep    build_ms     query_ms_prom  query_ms_med
---------------------- -------- -------- ------ ------------ -------------- --------------
VP-Tree (consultas)    500      1000     5      1.337        3.805          3.743
Lineal (consultas)     500      1000     5      0.000        49.997         50.197
VP-Tree (consultas)    2000     1000     5      6.522        4.151          4.159
Lineal (consultas)     2000     1000     5      0.000        197.563        197.379
VP-Tree (consultas)    10000    1000     5      40.331       4.861          4.761
Lineal (consultas)     10000    1000     5      0.000        999.616        995.475
AVL (insert)           50000    0        5      446.164      311.410        312.587
heapq (insert)         50000    0        5      9.412        29.406         29.331
```

Archivo generado: `benchmark_results.csv`.

## Nota sobre clustering
Existe [src/clustering.py](src/clustering.py) (clustering por conectividad Manhattan), pero actualmente **no se usa en la interfaz**.
