# Mantenimiento del PFC Wi-Fi CSI

## Propósito y alcance

El producto ejecuta adquisición CSI, procesamiento, reconocimiento binario con ESP32-C6 y experimentos exploratorios de adaptación con datos públicos. Incluye portal Django, CLI y herramientas de verificación. La tesis usa protocolos y criterios académicos propios. Mantén sus resultados y su código de investigación separados de los experimentos del PFC.

## Arquitectura y puntos de entrada

| Área | Responsabilidad |
| --- | --- |
| `src/pfc07/` | Lectura y representación CSI, clasificación, particiones, métricas y figuras. |
| `web_local/portal/` | Formularios, acceso por rol y propietario, experimentos, captura y exportación. Guarda metadatos en SQLite y artefactos en archivos locales. |
| `firmware/esp32c6/` | Fuentes y configuraciones TX/RX, huellas y atribución de Espressif. |
| `herramientas/` | Captura serie, auditoría por bloques, evaluación C6 y verificación del cierre. |
| `tests/`, `web_local/portal/test*.py` | Pruebas de núcleo y de integración del portal. |
| `datos_locales/`, `outputs/` | Entradas y artefactos locales excluidos de Git. |

**Instalación y ejecución.** Sigue [README.md](README.md). La referencia usa Python 3.12, Django, SQLite, NumPy, SciPy, scikit-learn, Matplotlib y pyserial. `INICIAR.cmd` administra la clave y el arranque local. Ejecuta `python -m pytest -q` y `python verificar_web.py` en el entorno virtual. Habilita `PFC_TEST_REAL_DATA` para validar comparaciones reales.

**Datos públicos.** Lee [DATOS_REALES.md](DATOS_REALES.md) al cambiar la lectura MAT, el registro de NPZ o el diseño experimental. Usa las mismas consultas para todos los valores K. Ajusta el escalador con origen, conserva el soporte y purga y compara 0/1/5/10 con combinación de probabilidades y ajuste convencional. Los ZIP originales son recursos externos.

**Captura y piloto C6.** Lee [CAPTURA_ESP32.md](CAPTURA_ESP32.md) para la configuración de TX/RX, el puerto serie, los archivos `raw.log` y `metadata.json` y el uso de modelos. El portal reconoce con el ambiente del modelo operativo. La evaluación Few-Shot C6 con soporte/consulta por sesión usa `herramientas/evaluar_fewshot_c6.py`. Sus reglas y métricas están en el [protocolo del piloto](docs/protocolo_fewshot_esp32_c6.md).

**Formatos y límites.** La demo sintética comprueba software y debe seguir identificada como artificial. Los NPZ públicos acompañados de JSON almacenan características y procedencia. Las capturas C6 almacenan pares I/Q y metadatos del enlace. Mantén sus modelos y métricas separados. Exporta predicciones, matrices y ajustes como CSV o JSON con configuración y huellas. El piloto tiene alcance descriptivo y las ventanas de una grabación son dependientes. Conserva SQLite y la ejecución loopback mientras el alcance sea local.

## Reglas para los cambios

1. Reutiliza la lógica existente. Sigue sus nombres y estilo de Python, usa rutas configurables y agrega dependencias solo cuando sean necesarias.
2. Fija particiones, semillas, filtros y comparadores antes de consultar resultados. Mantén disjuntos entrenamiento, soporte y consulta. Conserva registros y resultados desfavorables. Nunca inventes resultados ni ajustes el protocolo para favorecer métricas.
3. Registra procedencia, versión, configuración, roles y huellas. Documenta las limitaciones de la evidencia y distingue medición real, dato sintético y estimación.
4. Mantén fuera de Git credenciales, identificadores privados, capturas, modelos locales, datos sin autorización e informes académicos. Conserva atribuciones de terceros y los permisos por rol y propietario. Usa una instancia loopback para verificación.
5. Conserva el historial y las ramas existentes. Comprueba el diff y la procedencia antes de consolidar. No reescribas ni fuerces ramas publicadas.
6. Considera funcional un cambio cuando pase los tests pertinentes y el flujo normal, incluidas entradas ausentes y datos anteriores. Para cambios de métricas, recalcula desde las predicciones. Para cambios de instalación, verifica desde un clon limpio. Declara completado solo lo respaldado por evidencia.

Las ampliaciones posibles incluyen repetir con más sesiones y participantes, evaluar sensibilidad a geometría y mejorar la portabilidad de adquisición. Requieren un protocolo fijado y evidencias nuevas.
