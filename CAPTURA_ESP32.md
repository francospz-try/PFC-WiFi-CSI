# Captura y reconocimiento con ESP32-C6

## Operar el portal

1. Inicia el portal desde la raíz y entra con una cuenta administradora.
2. En **Captura ESP32**, selecciona actividad, uso, ambiente, dataset, geometría y duración. El formulario usa `COM7` y admite de 5 a 60 s. Libera el puerto en cualquier monitor serie antes de pulsar **Preparar captura**.
3. Mantén la actividad desde el inicio de la cuenta regresiva hasta el mensaje final. El capturador registra el inicio efectivo después de abrir el puerto.
4. Selecciona dos sesiones para visualizar amplitud y variabilidad temporal. Puedes descargar los registros originales. La comparación gráfica admite capturas existentes con las placas desconectadas.

La CLI admite otro puerto mediante `herramientas/captura_sesion.py --port COMx`. Consulta `--help` para los metadatos requeridos. Usa una sola instancia de captura por puerto. El receptor local entrega UART lógico por USB Serial/JTAG a 921600 baudios. Se registran paquetes `CSI_DATA` en `datos_locales/csi_piloto/<sesión>/raw.log`. El `metadata.json` guarda contexto, calidad, marcas de tiempo y SHA-256. Para importar una sesión autorizada, copia ambos archivos con la carpeta completa y contrasta la huella del registro.

## Reconocimiento y evaluación

- El control histórico requiere al menos 60 paquetes válidos por segundo, como máximo 10 % de saltos nominales y como máximo 1 % de filas malformadas. Los saltos no identifican por sí solos pérdidas de radio o de USB.
- Las ventanas retenidas miden un segundo y pasan controles de continuidad y tamaño. Se calculan seis indicadores de variación temporal de log-amplitud. La comparación gráfica usa una máscara por par para visualizar posiciones activas.
- En **Reconocer quietud y caminata**, el modelo local se ajusta con sesiones de aprendizaje y reconoce sesiones reservadas del mismo ambiente y dataset. La etiqueta se declara por grabación. La proporción de votos por ventana no es una probabilidad calibrada.
- La evaluación descriptiva C6 entre ambientes congela el modelo histórico y separa sesiones en soporte y consulta. Lee el [protocolo Few-Shot](docs/protocolo_fewshot_esp32_c6.md) para reproducir la comparación con entradas autorizadas. El controlador del C6 entrega 128 posiciones complejas de una antena en HT40.

Para repetir la campaña histórica, pasa a `herramientas/evaluar_fewshot_c6.py` las ocho carpetas de sesión del respaldo autorizado y usa `--modelo` para indicar el directorio del NPZ y JSON históricos congelados. El script verifica identidades y huellas. Ejecuta `python herramientas/verificar_fewshot_c6.py <directorio-de-salida>` para recalcular las métricas desde los CSV sin acceder al hardware.

## Firmware y reconstrucción

Las copias en `firmware/esp32c6/` corresponden a [Espressif ESP-CSI](https://github.com/espressif/esp-csi/tree/8633d67152db2808f141cc1595970aa9cf406045), revisión `8633d67152db2808f141cc1595970aa9cf406045`, ESP-IDF 5.5.6, objetivo `esp32c6`. El emisor usa ESP-NOW en canal 11 con una frecuencia nominal de 100 paquetes/s. El receptor estima CSI, filtra la identidad de enlace configurada por el ejemplo y serializa pares I/Q. Las copias C conservan los avisos del fabricante. La configuración local del receptor usa la consola USB Serial/JTAG. Las huellas están en `firmware/esp32c6/sha256.json`.

1. Clona ESP-CSI y selecciona la revisión fijada. Abre su entorno ESP-IDF 5.5.6.
2. Para TX usa `examples/get-started/csi_send`. Ejecuta `idf.py set-target esp32c6`, copia `tx_app_main.c` a `main/app_main.c` y `tx_sdkconfig` a `sdkconfig`.
3. Para RX usa `examples/get-started/csi_recv`. Ejecuta `idf.py set-target esp32c6` y copia los correspondientes `rx_app_main.c` y `rx_sdkconfig`.
4. Compila cada proyecto con `idf.py build`. Para una instalación nueva, programa la placa correspondiente con `idf.py -p COMx flash` y confirma que el RX presenta salida serie. Si ya tienes un montaje operativo, conserva su firmware y usa el paso de captura web para probarlo.

Consulta [atribuciones](TERCEROS.md) para las condiciones de distribución. Conserva los datos de campo y los identificadores físicos en un respaldo autorizado.
