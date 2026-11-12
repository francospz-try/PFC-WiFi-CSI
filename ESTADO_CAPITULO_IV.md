# Estado verificable del desarrollo — 30/10/2026

## Implementado y comprobado

- Firmware oficial ESP-CSI compilado y cargado en dos ESP32-C6; respaldos previos.
- Adquisicion CSI real con TX independiente y RX USB.
- Guardado de señal original, metadatos, etiquetas, fecha local y calidad.
- Portal para captura, comparacion grafica, descarga y consulta de firmware.
- Clasificador piloto por prototipos para quietud/caminata, con dos grabaciones
  iniciales del dataset piloto_inicial. Sin exactitud independiente medida.
- Separacion entre capturas para aprender y para probar reconocimiento.

## Hallazgos actuales

Las dos capturas recientes de casa_habitacion son de prueba, no de aprendizaje.
Reciben 33,1 y 36,4 registros/s y presentan numerosos saltos. No existe modelo
entrenado para casa_habitacion ni modelo de tres posturas.

Los umbrales >=60 registros/s y <=10% de saltos son decisiones iniciales de
ingenieria del piloto, no requisitos universales del CSI ni parametros validados
por la tesis. Deben justificarse o revisarse mediante un analisis de sensibilidad.
Los saltos de contador no localizan por si solos la causa de perdida.

La comparacion tecnica consecutiva recibio 80,1 registros/s con el capturador
anterior y 77,1 con lectura por bloques y analisis posterior, con RSSI -89 dBm.
Por tanto, no confirma que el capturador sea la causa principal de la degradacion.
Las condiciones fisicas y actividad no estuvieron controladas externamente.
Se conserva la mejora de estructura del capturador, sin atribuirle una recuperacion
de calidad demostrada. La causa de la caida entre sesiones queda sin determinar.

## Pendientes del experimento principal de tesis

- Auditar archivos internos S5/S6/S7, dimensiones y seleccion del receptor.
- Cerrar indices OFDM/LTF validos y preprocesamiento reproducible por plataforma.
- Implementar y ejecutar el modelo base previsto en la tesis.
- Ejecutar in-domain y 0-shot con particiones sin fuga de datos.
- Implementar comparaciones 1/5/10-shot y variante regularizada.
- Ejecutar rotaciones, repeticiones y analisis de sensibilidad.
- Adquirir y evaluar validacion propia por sesiones independientes.
- Integrar evidencia, decisiones reales y cambios de protocolo en el capitulo IV.

El clasificador binario de movimiento es un piloto de adquisicion y software;
no sustituye el experimento cross-environment de cinco actividades de la tesis.

## Porcentaje de avance

No se ha calculado ni acreditado un porcentaje global del capitulo IV. Para
acreditar el minimo funcional de la rubrica se requiere una linea base separada
del alcance completo, pesos que sumen 100%, criterios de terminado y evidencia
en video. La existencia de capturas o pantallas no acredita por si sola el 30%.
Este registro es una lista de evidencia y pendientes, no una calificacion.

## Siguiente comprobacion controlada

Conservar geometria y mantener fija la posicion de la persona. Comparar pruebas
cortas alternadas cambiando una sola condicion: alimentacion TX (powerbank frente
a cargador USB), despues despeje/orientacion si es necesario. Registrar calidad
y condiciones, sin confundir cada diagnostico con nuevas muestras HAR. No bajar
umbrales solo para obtener una prediccion. Tras estabilizar, adquirir ejemplos
etiquetados y pruebas independientes dentro de una misma campaña.


## Actualizacion posterior: auditoria publica completada en la seleccion

Se verificaron completamente las 15 grabaciones A/B/C/G/K del receptor a en S5/S6/S7, CRC correcto y sin componentes no finitas. Tambien se comprobaron los tres NPZ existentes (465x24), con valores finitos e identificadores de ventana unicos. Se localizaron evaluaciones publicas exploratorias previas del PFC: mi revision anterior no las habia tenido en cuenta. Esta actualizacion sustituye el pendiente de auditoria para esta seleccion; siguen pendientes la alineacion con el protocolo de tesis, la escala de S7 y la revision de particiones de las evaluaciones previas. Informe: outputs/auditoria_publicos_20261030/INFORME.md.
