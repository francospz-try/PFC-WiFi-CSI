# HANDOFF HAR PARA CHATGPT — auditoría 12/11/2026

## A. Estado general y recomendación

El producto adquiere CSI con dos ESP32-C6 y clasifica grabaciones completas mediante un piloto binario de quietud/caminar. El modelo operativo sí corresponde a `har_habitacion_1m`: se reconstruyeron sus parámetros con las seis sesiones y coinciden exactamente con el NPZ guardado. Las dos pruebas nuevas no participaron en ese ajuste ni en la evaluación interna. No se sobrescribió el modelo.

El sistema permite una **demostración mediante grabaciones reales previamente adquiridas**. Todavía no ofrece evidencia suficiente para anunciar reconocimiento robusto en vivo, generalización entre personas o ambientes, detección certificada de presencia ni conteo de personas. La prioridad es recopilar repeticiones independientes y validar estabilidad antes de ampliar el clasificador. Few-Shot con datos externos es una línea separada; no se ha demostrado sobre estos ESP32 propios.

## B. Datos reales e integridad

Proyecto: `C:\Franco\2026\PFC_implementacion`. Rama autorizada: `desarrollo/csi-captura-estable`. HEAD inicial: `95358a6873f90c5de308304b1b8accf1a7bd0dfd`; árbol inicial limpio.

Dataset `har_habitacion_1m`, habitación, TX-RX 1,2 m, TX 0,8 m y RX 0,4 m. Las ocho capturas conservan los mismos metadatos geométricos. La coincidencia documental no sustituye una medición independiente del montaje. Seis sesiones de aprendizaje y dos reservadas para reconocimiento, aproximadamente 60 s por sesión. Las actividades reales son declaraciones del operador por grabación; no existe anotación temporal independiente de cada ventana.

| Sesión (UTC) | Uso / actividad | CSI válidos | Hz¹ | Saltos | RSSI dBm | Ventanas |
|---|---|---:|---:|---:|---:|---:|
| `web_20261112T042701_463020_quieto` | Aprendizaje / quietud | 5426 | 90.43 | 27 | -78.0 | 55 |
| `web_20261112T043409_348410_caminar` | Aprendizaje / caminar | 5423 | 90.38 | 30 | -77.0 | 55 |
| `web_20261112T044206_346423_quieto` | Aprendizaje / quietud | 5390 | 89.83 | 63 | -80.0 | 55 |
| `web_20261112T044344_065512_caminar` | Aprendizaje / caminar | 5393 | 89.88 | 59 | -78.0 | 55 |
| `web_20261112T044532_455832_quieto` | Aprendizaje / quietud | 5396 | 89.93 | 56 | -79.0 | 55 |
| `web_20261112T044708_008871_caminar` | Aprendizaje / caminar | 5174 | 86.23 | 278 | -78.0 | 55 |
| `web_20261112T051105_835471_sin_etiquetar` | Prueba nueva / caminar | 5371 | 89.52 | 82 | -82.0 | 55 |
| `web_20261112T050341_476851_sin_etiquetar` | Prueba nueva / quietud | 5428 | 90.47 | 25 | -68.0 | 55 |

¹ La frecuencia usa CSI válidos / duración de captura registrada. El reloj del dispositivo y sus intervalos se recalcularon desde raw.log; la duración de pared del ordenador no se puede reconstruir exclusivamente desde ese archivo.

Todos los hashes de raw.log coinciden con los metadatos. Se guardó un manifiesto de integridad de capturas, metadatos, respaldo de corrección y modelo. El error histórico de distancia 0,2→1,2 m ya estaba corregido y auditado: no se repitió. Fue una corrección del metadato declarado por el operador, no una modificación de mediciones CSI.

Modelo NPZ SHA-256: `0e9dc88823ea738af141d0d1042899798b4bb47bb6bfeaec4d10dc36eb7d4e94`.

Informe JSON SHA-256: `0b3def536bfa0e06e1a55e96b3373c4f628fe62e7a7f3f45e2c8f50db776fb65`.

La fecha de entrenamiento no figura en el informe histórico. No se infiere a partir de la fecha de modificación del archivo. Las inferencias actuales con este hash reproducen los porcentajes comunicados por el operador; no existe un registro histórico con hash que pruebe de forma independiente qué archivo se cargó en aquellos dos clics originales.

## C. Método y arquitectura

ESP32-C6 TX → ESP-NOW, canal 11 → ESP32-C6 RX → USB serial a 921600 baudios → captura Python → raw.log y metadata.json → características temporales → prototipos HAR → Django. El firmware y COM7 no se tocaron en esta auditoría.

Cada paquete contiene 256 componentes enteros I/Q, convertidos a 128 amplitudes `hypot(I,Q)`. Se aplica `log1p(amplitud)`, sin unidades físicas calibradas. Para cada ventana de 1 s se calculan seis características: percentiles 25, 50, 75 y 90 de la desviación estándar temporal de las amplitudes logarítmicas por posición; mediana y percentil 90 de las diferencias temporales absolutas. El lector incluye las posiciones siempre nulas; no hay selección especializada de subportadoras, fase ni Doppler.

Ventanas no solapadas `[s,s+1)`, con `s` desde 2 hasta `int(t_final)-3`. La truncación del tiempo final elimina también su fracción residual; en estas capturas quedan 55 candidatas utilizables. Se exige ≥60 muestras y ningún intervalo >100 ms. Reglas de sesión: ≥60 registros/s, saltos nominales ≤10% y malformados ≤1%. La división de calidad nominal es saltos/(válidos+saltos), no una medida separada de pérdidas radio.

Normalización: media y desviación estándar de las ventanas del ajuste, con escala mínima 1e-6. Cada centro de clase es la media de las medias normalizadas por grabación: igual peso por sesión en los prototipos. Se usa distancia euclidiana al cuadrado y se asigna el centro más próximo. La actividad final es la clase mayoritaria; no hay clase desconocida, probabilidad calibrada ni filtro temporal. Los porcentajes son proporciones de ventanas asignadas.

## D. Evaluación y resultados

Orden de matrices: filas = actividad declarada; columnas = predicción; clases `[quietud, caminar]`.

**Evaluación interna:** ajuste con las primeras dos sesiones de cada clase y prueba con la última de cada clase. Entrenamiento: `042701`, `043409`, `044206`, `044344` (sufijos completos en la tabla). Prueba: `044532` quietud y `044708` caminar. Matriz **[[33, 22], [13, 42]]**, 110 ventanas, accuracy **68.18%**, F1 macro **0.6797**.

| Clase | Precision | Recall | F1 |
|---|---:|---:|---:|
| quietud | 0.7174 | 0.6000 | 0.6535 |
| caminar | 0.6562 | 0.7636 | 0.7059 |
| Macro | 0.6868 | 0.6818 | 0.6797 |

Quietud: 33/55 ventanas correctas (60%); caminar: 42/55 (76,36%). Por voto de grabación, ambas correctas: 2/2; F1 macro por grabación = 1. Eso son solamente dos grabaciones, no una estimación poblacional de 100%.

Después de esta evaluación, el modelo final se reajustó con las seis sesiones (330 ventanas). Por ello no debe evaluarse de nuevo sobre las dos sesiones internas y llamar independiente a ese resultado. No hubo fuga entre ajuste y prueba de la evaluación original: se reconstruyeron por separado los parámetros de las cuatro sesiones.

**Dos pruebas nuevas con modelo final congelado:** matriz **[[33, 22], [8, 47]]**, 110 ventanas, accuracy **72.73%**, F1 macro **0.7228**.

| Clase | Precision | Recall | F1 |
|---|---:|---:|---:|
| quietud | 0.8049 | 0.6000 | 0.6875 |
| caminar | 0.6812 | 0.8545 | 0.7581 |
| Macro | 0.7430 | 0.7273 | 0.7228 |

Caminar `051105`: 47/55 ventanas caminar (85,45%), 8 quietud (14,55%); mayoría caminar. Quietud `050341`: 33/55 quietud (60%), 22 caminar (40%); mayoría quietud. Por grabaciones: matriz `[[1,0],[0,1]]`, accuracy y F1 macro 1 sobre solo dos casos. Estos ensayos no se usaron para escoger hiperparámetros. Como ahora fueron inspeccionados, cualquier futura decisión basada en sus errores requiere un nuevo conjunto final intacto.

Las ventanas contiguas son correlacionadas; 110 ventanas no equivalen a 110 ensayos independientes. No se presentan intervalos binomiales por ventana como incertidumbre estadística defendible.

## E. Problemas, causas comprobadas e hipótesis

El principal problema experimental es la confusión sostenida de quietud: 40% de sus ventanas se asignan a caminar tanto en la evaluación interna como en la prueba nueva. Acertar el voto final oculta esa inestabilidad. Se exportaron predicciones temporales, distancias a ambos prototipos e intervalos de error para localizarla.

Los indicadores agregados tienen solapamiento entre clases y variación entre grabaciones. El clasificador usa varios percentiles relacionados de variabilidad, de modo que la distancia suma dimensiones redundantes. La normalización no elimina los cambios de canal ni las diferencias entre sesiones. RSSI se auditó como indicador de recepción; no es una de las seis características y su asociación no prueba causalidad.

La última caminata tiene 278 saltos sobre 5174 válidos (aprox. 5,10% nominal), por debajo del umbral 10%. Conserva 55 ventanas utilizables. No se descarta automáticamente: más saltos no demuestran que sea la causa de los errores. No se observaron reinicios temporales que expliquen las confusiones.

Movimientos leves durante quietud, multipath, orientación del cuerpo y montaje son hipótesis, no causas demostradas. Faltan video/anotación temporal y repeticiones controladas. El tamaño reducido y una única campaña impiden separar actividad, sesión y condiciones del canal.

Problemas de software reproducidos: el POST de reconocimiento perdía la selección tras redirigir; la respuesta no identificaba dataset/hash del modelo ni actividad declarada; el entrenamiento no filtraba explícitamente el propósito de captura; el formulario usaba geometría fija. Las dos pruebas actuales tenían etiqueta sin_etiquetar y por eso no habían contaminado el entrenamiento; el riesgo afectaba capturas reservadas que conservaran una etiqueta de actividad.


La resustitución con el modelo final obtiene [[139,26],[50,115]]: 76,97% por ventanas y 5/6 grabaciones por mayoría. La primera caminata de aprendizaje se clasifica mayoritariamente como quietud (29 frente a 26 ventanas); es una limitación real, no una prueba independiente.

En quietud nueva los errores están en [2,4), [5,10), [24,26), [35,38), [39,40), [47,48), [49,57) s. En caminar nuevo: [10,12), [26,27), [31,33), [44,46), [56,57) s, desde el primer CSI utilizable. El RSSI mediano es −68 dBm en quietud nueva y −82 dBm en caminar nuevo, frente a −77 a −80 dBm en aprendizaje. Es una diferencia de 14 dB entre dos sesiones, confundida con actividad; no una causa probada.

La extracción offline de características tardó 6,21–8,87 s por grabación, incluyendo lectura y parseo; inferir un lote de 55 ventanas tardó aproximadamente 0,03–0,05 ms (promedio de 1000 repeticiones). El parseo domina este recorrido offline. No son medidas de latencia de adquisición en vivo.

## F. Archivos relevantes y reproducción

Rutas relativas a `C:\Franco\2026\PFC_implementacion`:

- `src/pfc07/csi_reconocimiento.py`: características, ajuste, separación interna y predicción.
- `src/pfc07/csi_piloto.py`: lectura CSI y comparación descriptiva.
- `herramientas/captura_sesion.py`: adquisición original; no modificado.
- `web_local/portal/reconocer_views.py`, `csi_views.py`: vistas y formulario.
- `web_local/templates/csi_reconocer.html`, `csi_piloto.html`: pantallas.
- `herramientas/auditar_har_piloto.py`: reconstrucción independiente y manifiestos.
- `herramientas/figuras_har_feria.py`: figuras derivadas.
- `outputs/feria_2026/auditoria/resultados.json`, `ventanas.csv`, `ventanas_evaluacion_interna.json`: métricas, tiempos y decisiones verificables.

Reproducir desde el proyecto con `.venv\Scripts\python.exe herramientas\auditar_har_piloto.py` y después `.venv\Scripts\python.exe herramientas\figuras_har_feria.py`. No abren el puerto ni sobrescriben el modelo; reconstruyen parámetros en memoria y generan derivados dentro de outputs.

## G. Correcciones y pruebas

Se conservan dataset, modo y sesión seleccionados tras el POST; el resultado identifica la actividad declarada y predicha, la grabación, dataset y hash del modelo. La página muestra la matriz interna con orientación explícita. Se agrupan capturas por dataset y propósito. El formulario recupera geometría/duración/dataset/ambiente de la captura más reciente; actividad y propósito quedan sin seleccionar para requerir una decisión nueva. Los metadatos históricos no se actualizan al rellenar ese formulario.

El entrenador excluye los propósitos explícitos reconocer y enlace y mantiene compatibilidad con capturas antiguas sin campo de propósito. Los nuevos informes registran fecha UTC; el modelo histórico conserva fecha desconocida. No se cambió la fórmula del clasificador ni sus parámetros operativos.

Pruebas iniciales: pytest 26 aprobadas; Django 27 ejecutadas, una omitida. Se añadieron regresiones temporales para propósito, identidad del modelo, selección tras éxito/error, configuración, timestamp y JSON ilegible. Los resultados finales y commits se registran en el cierre de este documento. Las pruebas sintéticas validan software, no constituyen evidencia de rendimiento HAR. No se realizaron pruebas físicas ni se abrió COM7.

## H. Git y protección

Cambios de software y pruebas separados de documentación y generadores en commits coherentes sobre `desarrollo/csi-captura-estable`. Los datasets, NPZ y evidencias derivadas permanecen excluidos en datos_locales/ y outputs/. Se revisan diff, exclusiones, integridad y suites antes de subir la rama. main y respaldo/lab08-local no se modifican.

## I. Siguiente implementación y capturas necesarias

1. Congelar el modelo y protocolo actuales. Recopilar **12 grabaciones nuevas de 60 s**, seis quietud y seis caminar, en tres bloques temporales de cuatro (dos por clase), alternando el orden y manteniendo la geometría. Destinarlas exclusivamente a evaluación; registrar postura, trayectoria, interrupciones y marcas de inicio/fin. Esto comprueba repetibilidad local, no población.
2. Si se decide comparar selección de posiciones activas, características menos redundantes o normalización robusta, adquirir **12 grabaciones adicionales de desarrollo**, seis por clase, separadas de las 12 de evaluación. Comparar con validación por grabaciones o bloques, nunca ventanas aleatorias, y fijar método antes de abrir el conjunto final.
3. Incluir **cuatro controles de 60 s** fuera de las clases (dos habitación vacía y dos actividad distinta) para caracterizar rechazo; el modelo binario actual no debe interpretarlos como presencia/ausencia fiable. Un corte de datos se prueba con reproducción de un archivo interrumpido, sin abrir hardware.
4. Solo después de fijar criterios y validar: desacoplar lector serial (cola acotada), procesador de ventanas y UI. Reutilizar las seis características y modelo congelado; comenzar con ventanas de 1 s y actualización cada 1 s para mantener el protocolo. Si se introduce solapamiento, validarlo aparte.
5. Mostrar historial, tiempo del último paquete, validez y latencia. Ante datos insuficientes mostrar SIN DATOS, nunca quietud. Un voto temporal debe evaluarse con sus retrasos y errores, no esconder inestabilidad. Medir latencia extremo a extremo y pérdida de paquetes; un benchmark offline no valida captura en vivo.
6. Ensayar primero reproducción offline con marcas de tiempo, luego una captura física controlada. ESPressif wifi_sensing_demo, router antiguo y nuevas arquitecturas quedan como alternativas posteriores. No se añade tercer ESP32 ni conteo.

## J. Evidencias para la feria

Paquete `outputs/feria_2026/`: capturas reales de Django, figuras SVG/PNG de señales, calidad, matrices, proporciones, arquitectura y evolución temporal; auditoría tabular; guía de demostración; inventario con fuente/fecha/alcance. No se creó el póster definitivo ni diapositivas.

El experimento externo S5→S6 existente se comprobó desde sus predicciones guardadas: accuracy 7,09% (0-shot), 6,84% (1-shot), 7,09% (5/10-shot), 395 ventanas de consulta compartidas y soporte disjunto. Es un resultado limitado/negativo de datos externos; no demuestra adaptación Few-Shot en los ESP32. No se volvieron a leer los ZIP ni a entrenar ese experimento.

Pendientes físicos: fotografías reales del montaje completo, TX, RX, alturas/distancia y trayectoria; no se sustituyen por imágenes genéricas. Para la feria se recomienda la demostración con grabaciones, no anunciar inferencia en directo.

## K. Cierre de verificación y archivos entregados

Pruebas finales: **30/30 pytest aprobadas**, **32 pruebas Django ejecutadas: 31 aprobadas y una omitida**. La omitida requiere activar PFC_TEST_REAL_DATA para una integración adicional con NPZ externos; el HAR propio sí fue auditado con sus archivos reales. La revisión independiente no encontró bloqueos; se corrigió además el hash de inferencia para calcularlo sobre los mismos bytes cargados del NPZ, con regresión RED→GREEN. Se verificaron de nuevo las dos inferencias y los 20 hashes originales después de esa corrección.

Pendiente menor de interfaz: si se elimina manualmente una sesión entre seleccionarla y enviarla, el comportamiento existente responde 404 en vez de redirigir con mensaje. No se eliminó ninguna sesión. Los modelos JSON/NPZ aún son dos archivos separados; una futura operación concurrente de entrenamiento requiere publicación atómica de ambos. Esta auditoría no entrenó concurrentemente.

Commits de esta entrega: `14d4c05` correcciones; `b68c316` pruebas; `7226393` auditoría y figuras. La documentación está en el commit titulado `docs: documentar diagnostico HAR y evidencias de feria` que contiene este archivo; su identificador se entrega también en la respuesta final. Rama de publicación: desarrollo/csi-captura-estable. No hay datasets ni evidencias pesadas versionados. main y respaldo/lab08-local conservan sus referencias originales.

Archivos de software modificados: src/pfc07/csi_reconocimiento.py; web_local/portal/csi_views.py; web_local/portal/reconocer_views.py; web_local/templates/csi_piloto.html; web_local/templates/csi_reconocer.html. Pruebas: tests/test_csi_reconocimiento.py y web_local/portal/test_csi_piloto.py. Nuevos generadores: herramientas/auditar_har_piloto.py y herramientas/figuras_har_feria.py. Documentación: docs/diagnostico_har_piloto.md, docs/HANDOFF_HAR_PARA_CHATGPT.md, docs/feria_2026_contenido_poster.md y docs/plan_auditoria_har_20261112.md.

Capturas reales (JPG nativos del navegador), dentro de `outputs/feria_2026/capturas_web/`:

- 01_dashboard.jpg
- 02_capturas_sesiones_comparacion.jpg
- 03_formulario_captura.jpg
- 04_evaluacion_interna_confusion.jpg
- 05_reconocimiento_caminar.jpg
- 06_reconocimiento_quietud.jpg
- 07_externo_S5_S6_fewshot_limitado.jpg

Figuras, cada una en SVG editable y PNG de alta resolución, dentro de `outputs/feria_2026/graficos/`:

- A_senales_csi
- B_calidad_adquisicion
- C_evaluacion_interna
- D_pruebas_nuevas_matriz
- D_proporciones_ventanas
- E_arquitectura
- F_predicciones_temporales

Inventario: `outputs/feria_2026/inventario_evidencias.json`, con fuente real, fecha, dataset/sesión, alcance, ruta y hash. Guía física: `outputs/feria_2026/fotografias_pendientes.md`. Procedimiento: `outputs/feria_2026/demostracion/GUIA_DEMOSTRACION.md`. Matriz de preparación: `outputs/feria_2026/demostracion/matriz_preparacion.md`. No se grabó video; se dispone de capturas verificadas y un recorrido reproducible.

Para demostrar sin hardware: desde el proyecto ejecutar `.venv\Scripts\python.exe outputs\feria_2026\demostracion\servidor_evidencia.py` y abrir http://127.0.0.1:8766/. Usa SQLite temporal y alias de exposición; bloquea entrenamiento/captura. Mostrar las dos sesiones reservadas y comprobar su identificador y el hash del modelo. Cerrar con Ctrl+C. No exponer esa instancia a la red.

Estado para la feria: listo con limitaciones para mostrar adquisición histórica, inspección CSI y clasificación de grabaciones. Fotografías físicas pendientes. Reconocimiento en vivo, generalización y Few-Shot propio permanecen pendientes. El operador debe aportar vista general, TX, RX, ubicación/alturas/distancia y trayectoria; no se fabricaron fotografías.
