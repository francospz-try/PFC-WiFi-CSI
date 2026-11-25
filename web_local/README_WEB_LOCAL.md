# Portal local del PFC

La instalación y el primer inicio se documentan en el [README del repositorio](../README.md). El administrador mantiene el catálogo, controla capturas y puede consultar todos los experimentos. El investigador crea, consulta y exporta sus propios experimentos. SQLite y los artefactos de ejecución se crean localmente.

Las guías de [datos públicos](../DATOS_REALES.md) y [ESP32-C6](../CAPTURA_ESP32.md) explican los requisitos de cada flujo. Los resultados reales incluyen dos comparadores y permisos sobre métricas, matrices y exportaciones. La prueba sintética comprueba el flujo con entradas artificiales.

Para verificar la integración desde la raíz ejecuta `python verificar_web.py` en el entorno virtual. Define `PFC_TEST_REAL_DATA` con el directorio de derivados públicos para habilitar la prueba de datos reales. El alcance verificado es el servidor local en la interfaz loopback.
