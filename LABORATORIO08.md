# Laboratorio 08 — Pruebas del producto Wi-Fi CSI

## Alcance y relación con el proyecto acumulativo

Este documento agrega evidencia de la Práctica 08 al producto existente. No reemplaza los capítulos previos ni modifica los wireframes. El caso principal es B (entrenamiento de modelos de IA), complementado con integración, seguridad y un recorrido de la interfaz del Caso A.

Referencia de requisitos: guía local `PFC PRÁCTICA 08-2026 (1).pdf`, actividades de las páginas 11–12 y rúbrica de las páginas 14–15. Aunque la portada y las actividades identifican la Práctica 08, algunos encabezados y la rúbrica conservan “Práctica 04”; se registra esa inconsistencia sin corregir el original. La rúbrica asigna 35 % a pruebas funcionales, 35 % a no funcionales, 10 % al informe y 20 % a la exposición.

## Entorno y protección de los datos

- Windows, entorno virtual existente, Python/Django/SQLite y scikit-learn. Sin nuevas dependencias.
- Commit de partida: `73a49c036444801f8c43259a24cbb44efe142b9a`. Cambios de laboratorio sin commit ni push.
- Entradas: `datos_locales/S5_real.npz`, `S6_real.npz`, `S7_real.npz` y sus metadatos JSON.
- Los NPZ se leen sin modificarlos. No se regeneraron desde MAT para esta ejecución.
- Pruebas web con base de pruebas y carpetas temporales. Recorrido visual con `servidor_lab08.py`, una base descartable y una cuenta de investigador de prueba.
- Las capturas corresponden a la interfaz real del producto en esa instancia aislada, no a maquetas. Los datos usados para evaluar son los NPZ reales.
- Evidencias de esta entrega: `outputs/laboratorio08_entrega/`. Las mediciones contienen hashes de entradas y código, versiones, semillas y fecha UTC. Para el documento académico, expresar las fechas en America/Lima.

## Protocolo experimental

Cada escenario aporta 465 ventanas, 93 por cada una de las cinco actividades A/B/C/G/K. Se utilizan 24 estadísticas de amplitud, receptor a, antena 0, ventanas no superpuestas de 128 paquetes. La normalización se ajusta únicamente sobre el entrenamiento origen.

La comparación entre ambientes usa las primeras diez ventanas de cada clase como conjunto elegible de soporte, cuatro ventanas de separación y 79 ventanas por clase como consulta: 395 consultas compartidas. Los soportes 1/5/10 son anidados dentro de cada semilla. Se ejecutan seis direcciones, cinco semillas (7, 21, 42, 84, 123) y cuatro configuraciones: 120 filas de métricas. Las semillas cambian el soporte; no crean nuevos sujetos ni sesiones independientes. Con 10-shot se usan los diez soportes, por lo que variar su orden no aporta variabilidad experimental.

La validación dentro del ambiente usa las primeras 55 ventanas por clase para entrenar, omite cuatro y evalúa las 34 restantes. Es un diagnóstico temporal de una misma grabación, no una validación con sesiones nuevas. No se hizo selección de hiperparámetros con la consulta final.

## Casos funcionales

| ID | Prueba y entrada | Resultado esperado / criterio | Resultado observado y evidencia |
|---|---|---|---|
| F01 | Predicción 0/1/5/10 sobre NPZ reales | Cuatro métricas finitas, consulta común y soporte de 5×k muestras | Ejecutado en las seis direcciones y cinco semillas; `resumen.csv`, `cross_domain.csv` y protocolos por ejecución |
| F02 | Recalcular accuracy y F1 desde predicciones guardadas | Concordancia numérica con el CSV de métricas | Prueba automatizada aprobada; `test_reproducibilidad_y_metricas_desde_predicciones` |
| F03 | Validación temporal dentro del ambiente | Medir entrenamiento y consulta separada con purga; no reutilizar consulta en ajuste | Ejecutada; `validacion_temporal.csv`. No se definió un umbral académico de aceptación de exactitud |
| F04 | Entradas con NaN/Inf, dimensión errónea, etiquetas o longitudes incompatibles, orden duplicado o sesiones mezcladas | Rechazo antes de crear resultados | Siete casos parametrizados aprobados |
| F05 | Shots vacíos, repetidos o fuera de 0/1/5/10 | Error controlado y preservación de evidencia previa | Cuatro casos parametrizados aprobados |
| F06 | ZIP con variable csi y antenas separadas | Leer el eje de antena correcto y producir 24 características | Fixture artificial en formato real aprobado; no se reporta como experimento CSI real |
| F07 | Flujo real Django: ejecución, persistencia, detalle, gráfico y exportación | REAL_COMPLETADO y resultados para los cuatro k | Prueba con NPZ reales aprobada; `django_tests.txt` |
| F08 | Recorrido de navegador: login, catálogo, creación, ejecución y descarga | Completar el flujo con resultados reales y CSV coherente | Completado; cuatro capturas y `exportacion_navegador.csv` |

Las pruebas funcionales del software pasan, pero eso no equivale a aprobar la calidad predictiva. Un criterio mínimo de exactitud/F1 debe acordarse antes de la validación final, no elegirse después de observar estos resultados.

## Resultados reales y hallazgos

| Ambiente | Exactitud de entrenamiento | Exactitud de prueba temporal |
|---|---:|---:|
| S5 | 95,64 % | 88,24 % |
| S6 | 91,27 % | 87,65 % |
| S7 | 99,27 % | 82,94 % |

Los valores de entrenamiento no son estimaciones de generalización. Las diferencias respecto a la consulta temporal, especialmente en S7, requieren atención.

| Dirección | 0-shot | Mezcla actual 10-shot | Solo prototipos 10-shot (diagnóstico) |
|---|---:|---:|---:|
| S5 → S6 | 7,09 % | 7,09 % | 73,16 % |
| S5 → S7 | 20,00 % | 20,00 % | 75,70 % |
| S6 → S5 | 32,41 % | 32,15 % | 66,33 % |
| S6 → S7 | 20,76 % | 20,76 % | 69,37 % |
| S7 → S5 | 20,00 % | 20,00 % | 65,57 % |
| S7 → S6 | 20,00 % | 20,00 % | 72,41 % |

La adaptación en producción sigue siendo la mezcla fija de 50 % base y 50 % prototipos. La columna adicional usa el mismo escalador origen y soporte destino, pero peso de prototipos 1, como diagnóstico. No se cambió automáticamente el modelo web ni se eligió ese método como ganador validado. Al haberse inspeccionado esta consulta, una decisión posterior sobre el método requerirá validación separada antes de afirmar mejora final.

Estos resultados apoyan investigar el efecto de la combinación de probabilidades; no prueban que esa sea la única causa de degradación. La exactitud de 20 % en cinco clases balanceadas puede corresponder a predecir una sola clase: deben revisarse conjuntamente F1 macro y matrices.

## Casos no funcionales

| ID | Categoría | Procedimiento y evidencia | Alcance / resultado |
|---|---|---|---|
| NF01 | Rendimiento | Inferencia del baseline con 395, 3.950 y 39.500 filas; calentamiento y siete repeticiones; `rendimiento.csv` | Mediana, percentil 95 y muestras/s. No incluye lectura de MAT, entrenamiento, red ni Few-Shot |
| NF02 | Recursos | Tamaño de entrada y máximo de asignaciones rastreadas durante una inferencia adicional, separado del cronometraje | `tracemalloc` no mide RAM total ni necesariamente todas las reservas nativas. No se afirma consumo total del proceso |
| NF03 | Escalabilidad | Volumen creciente de ventanas replicadas y 90 GET autenticados distribuidos entre 1/4/8 hilos | 90/90 respuestas correctas; `http_carga.csv`. Replicar ventanas sirve para carga, no aumenta evidencia científica |
| NF04 | Robustez y tolerancia | Entradas inválidas, archivo ausente, rutas inválidas y ruido gaussiano de 0/0,01/0,05/0,1 desviaciones del origen | Rechazos controlados cubiertos por pruebas; `robustez.csv` registra exactitud/F1 y cambios de predicción |
| NF05 | Seguridad | Sesión obligatoria, aislamiento por propietario, POST, CSRF, límite de login y contención de rutas | Casos automatizados aprobados; solicitud HTTP de un experimento ajeno devuelve 404 |
| NF06 | Interpretabilidad | Descomponer el logit de una predicción base por dirección en aportes de características | Se verifica que suma de aportes + intercepto coincide con el logit; cinco aportes principales en `explicaciones_base.csv` |

Carga HTTP registrada: medianas aproximadas de 29,84 ms, 103,06 ms y 196,00 ms para 1, 4 y 8 hilos; máximos observados de 50,73 ms, 200,66 ms y 595,85 ms. Son mediciones locales del servidor de desarrollo, con una misma sesión de investigador; no certifican capacidad de producción, usuarios independientes, estrés hasta ruptura ni entrenamiento concurrente. Criterio funcional de esta prueba de carga: las 90 respuestas deben ser 200 y contener la sesión autenticada correcta; se cumplió. No se impuso un SLA de latencia no acordado.

Las perturbaciones son un ensayo de sensibilidad, no un ataque adversarial optimizado. Una predicción constante puede parecer robusta al ruido y seguir siendo incorrecta. La seguridad del modelo no queda certificada por los controles de acceso web.

Las explicaciones identifican grupo de subportadoras y estadística (media, desviación o cambio temporal) con su aporte al logit. No son porcentajes causales, no explican el movimiento físico y no cubren todavía la mezcla Few-Shot. Su comprensión por usuarios no técnicos requiere una sesión de aceptación; no se inventó esa evaluación.

## Estado de las pruebas y límites pendientes

- 23 pruebas del núcleo y 18 de Django: **41 aprobadas**, sin pruebas omitidas cuando se define `PFC_TEST_REAL_DATA`.
- El flujo real de navegador y la descarga CSV están verificados en la instancia aislada.
- Permanece pendiente la aceptación visual del usuario y la evaluación de comprensión de explicaciones.
- No se hicieron pruebas destructivas de hardware, agotamiento de disco/memoria, interrupción de energía ni estrés hasta ruptura.
- Falta evaluar entrenamiento concurrente y recuperación ante interrupción de escrituras; no se presenta como resuelto.
- No se afirma compatibilidad ESP32, generalización a otras personas/días ni mejora científica definitiva.
- La baja eficacia de la mezcla actual constituye un hallazgo abierto, no una prueba aprobada de mitigación cross-domain.

## Capturas para incorporar al documento acumulativo

Solo cuatro figuras necesarias, dentro de `outputs/laboratorio08_entrega/capturas/`:

1. `01_acceso.jpg`: pantalla de acceso, sin contraseña ni cuenta personal.
2. `02_datasets_reales.jpg`: catálogo S5/S6/S7 con revisión y receptor.
3. `03_configuracion_experimento.jpg`: origen S6, destino S5 y semilla 42 antes de guardar.
4. `04_resultados_y_matrices.jpg`: estado real completado, métricas 0/1/5/10, gráfico y matrices de confusión. Captura completa de página; al maquetar, puede distribuirse en más de una figura sin alterar su contenido.

Ubicarlas en la sección nueva de pruebas del producto. Mantener capítulos anteriores y referenciarlos para arquitectura y requisitos. Los archivos CSV/JSON y registros de ejecución complementan las figuras; las capturas no sustituyen la evidencia cuantitativa. La autorización por propietario se demuestra mediante registros HTTP y pruebas automatizadas, evitando otra captura redundante de una página 404.

## Reproducción

Desde PowerShell en la carpeta del proyecto:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
$env:PFC_TEST_REAL_DATA = (Resolve-Path datos_locales).Path
.\.venv\Scripts\python.exe -B verificar_web.py
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
.\.venv\Scripts\python.exe -B laboratorio08.py --salida outputs/laboratorio08_nueva_ejecucion
```

La salida debe ser una carpeta nueva: el script rechaza sobrescribir evidencias existentes. `verificar_web.py` establece una clave temporal para ejecutar las pruebas. Sin `PFC_TEST_REAL_DATA`, la integración con NPZ reales se omite explícitamente, no se considera aprobada.

Para repetir la prueba visual y HTTP, en una terminal:

```powershell
.\.venv\Scripts\python.exe -B servidor_lab08.py
```

Abrir `http://127.0.0.1:8768/login/`. La instancia se limita a localhost y crea únicamente una cuenta descartable `investigador_lab08`, contraseña de prueba `Lab08_temporal_2026!`. No son credenciales del sistema habitual. Un experimento de otro propietario se crea con ID 1 para comprobar aislamiento. Detener con Ctrl+C al terminar; su base temporal se descarta.

En otra terminal:

```powershell
.\.venv\Scripts\python.exe -B verificar_http08.py --salida outputs/laboratorio08_http_nuevo
```

## Registro de cambios

| Archivo | Motivo |
|---|---|
| `src/pfc07/procesamiento.py` | Validar contrato de características y conservar campos adicionales del NPZ |
| `src/pfc07/evaluacion.py` | Rechazar datos, semillas y shots inválidos antes de escribir artefactos |
| `web_local/portal/tests.py` | Aislar datos y resultados de las pruebas existentes |
| `tests/test_laboratorio08.py` | Casos de entradas, reproducibilidad, métricas y formato ZIP real con fixture artificial |
| `web_local/portal/test_laboratorio08.py` | Integración con NPZ reales y controles de acceso/fallos |
| `laboratorio08.py` | Generar mediciones reales, comparación diagnóstica, rendimiento, sensibilidad y explicaciones |
| `servidor_lab08.py` | Instancia temporal para revisión visual y HTTP sin modificar la base habitual |
| `verificar_http08.py` | Carga GET acotada y verificación HTTP de autorización |
| `LABORATORIO08.md` | Casos, resultados, límites, reproducción y ubicación de capturas |

No se cambió la arquitectura, la interfaz, las dependencias, las exclusiones de Git ni el algoritmo del modelo de producción.
