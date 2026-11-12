# Captura ESP32 integrada en el PFC

## Abrir

Inicia el proyecto con INICIAR.cmd, entra con tu cuenta administradora y pulsa
**Captura ESP32** en el menu. Ruta local: `/captura-csi/`.

La seccion permite consultar las sesiones importadas del piloto, comparar dos
grabaciones, descargar sus registros originales e iniciar una nueva captura.
El receptor debe estar en COM7 y ningun monitor serie puede tenerlo abierto.
La captura web usa un proceso local y espera hasta 30 segundos; no es streaming
continuo. Solo se admite una captura web simultanea por proceso del servidor.
Usa una sola instancia del servidor para operar las placas.

La cuenta regresiva de cinco segundos prepara al operador. El inicio efectivo
ocurre cuando el proceso abre el puerto y puede demorarse unos segundos. Mantén
la condicion elegida hasta ver el mensaje de finalizacion. Este piloto no tiene
sincronizacion externa de etiquetas; conviene excluir transiciones en el futuro.

## Datos y resultados

- Las dos sesiones iniciales se copiaron sin modificar desde el disco externo.
- Las nuevas capturas web se guardan en `datos_locales/csi_piloto` del PFC.
- No se sincronizan automaticamente con el disco externo.
- Cada sesion tiene `raw.log` y `metadata.json`, que incluye la huella SHA-256.
- Las comparaciones se calculan con el codigo del propio PFC, no con imagenes
  predibujadas. La pagina permite elegir las dos sesiones.
- La mascara de posiciones no nulas es exploratoria y depende del par comparado.
  No se debe reutilizar como selector de entrenamiento y prueba.

Los graficos comparan log(1 + magnitud I/Q) y variabilidad temporal por segundo.
No hay clasificador HAR integrado para estas capturas, exactitud ni mejora
cross-domain demostrada. El modulo de experimentos existente sigue siendo
independiente; no se mezclan sus metricas con este piloto.

## Firmware

En `firmware/esp32c6` se guardan copias de los fuentes y sdkconfig utilizados:

- TX: `tx_app_main.c`, placa MAC base 54:32:04:0c:c7:d0.
- RX: `rx_app_main.c`, placa MAC base 54:32:04:0c:b6:44.
- `sha256.json`: huellas de las copias.

Procedencia: Espressif ESP-CSI, commit
8633d67152db2808f141cc1595970aa9cf406045; ESP-IDF 5.5.6; objetivo esp32c6.
Se conservan las cabeceras originales de autoria y licencia. No se atribuye
como codigo original del PFC el ejemplo del fabricante.

El emisor usa ESP-NOW y un contador, con canal 11 y tasa nominal 100 Hz. La tasa
observada se mide aparte. El receptor estima CSI mediante el controlador Wi-Fi,
filtra la MAC configurada y serializa metadatos y componentes. Cambio local:
consola USB Serial/JTAG en el receptor. La laptop realiza el analisis.

Cambiar estos archivos de consulta no reprograma las placas. La compilacion y
programacion se realizan desde los proyectos originales de ESP-CSI. El respaldo
del firmware previo esta en el disco externo, `implementacion/respaldos`.

## Desarrollo

- `src/pfc07/csi_piloto.py`: lector y figura exploratoria.
- `web_local/portal/csi_views.py`: vistas, permisos y captura.
- `herramientas/captura_sesion.py`: adquisicion y calidad.
- `requirements-captura.txt`: dependencia pyserial.
- `web_local/portal/test_csi_piloto.py`: pruebas sin hardware real.

Para instalar comunicacion serie en un entorno nuevo:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-captura.txt
```

Para evaluar la hipotesis de tesis faltan repeticiones/sesiones independientes,
auditoria del dataset publico, preprocesamiento definitivo y el protocolo de
entrenamiento y adaptacion especificado en la tesis.
