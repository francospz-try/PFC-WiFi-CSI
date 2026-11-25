# PFC Wi-Fi CSI

Aplicación local de reconocimiento de actividades humanas mediante Wi-Fi CSI. Permite adquirir y comparar señales de dos ESP32-C6, ejecutar experimentos exploratorios de transferencia entre ambientes con datos públicos y exportar métricas. El portal Django y la CLI comparten el núcleo Python.

## Instalar y arrancar en Windows

Requisitos: Git, Python 3.12, PowerShell y permisos de escritura en el clon. Los ESP32 y los datos públicos son necesarios solo para sus flujos respectivos.

```powershell
git clone https://github.com/francospz-try/PFC-WiFi-CSI.git
cd PFC-WiFi-CSI
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt -r requirements-captura.txt
.\.venv\Scripts\python.exe -m pip check
.\INICIAR.cmd
```

El lanzador crea la clave local, aplica las migraciones de SQLite, solicita un administrador en el primer inicio y registra dos entradas sintéticas. Abre [el portal local](http://127.0.0.1:8000/login/). En `/admin/`, el administrador puede crear cuentas de investigación. Usa `Ctrl+C` en la terminal del servidor para detenerlo.

1. **Comprobar la instalación.** Crea un experimento con dos entradas DEMO y pulsa **Ejecutar DEMO sintética**. Usa el detalle para abrir métricas y matrices y exportar el CSV.
2. **Comparar ambientes con datos reales.** Prepara y registra los conjuntos S5, S6 y S7 según la [guía de datos](DATOS_REALES.md). Crea un experimento con dos datasets reales, por ejemplo S5 → S6. Pulsa **Ejecutar CSI real · 0/1/5/10-shot**. El detalle presenta combinación de probabilidades y ajuste convencional, con matrices y exportaciones por separado.
3. **Mostrar señales propias.** Con una cuenta administradora, abre **Captura ESP32** y elige dos sesiones autorizadas. Puedes reproducir capturas existentes si las placas están desconectadas. Para adquirir entradas nuevas o calibrar el reconocimiento, consulta la [guía técnica ESP32](CAPTURA_ESP32.md).

## Verificar y mantener

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe verificar_web.py
```

Con `PFC_TEST_REAL_DATA` apuntando al directorio de derivados verificados se habilita la prueba de integración con CSI real. `herramientas/verificar_cierre.py` ensaya migración, respaldo, restauración y carga HTTP en una instancia aislada. El puerto local 8768 debe estar libre. Consulta [AGENTS.md](AGENTS.md) para conocer la arquitectura, las reglas de cambios y los criterios de verificación.

## Alcance y recursos externos

La evaluación pública usa ventanas de grabaciones compartidas con bloques temporales disjuntos. El piloto C6 separa grabaciones completas por rol y evalúa quietud y caminata. Los resultados describen los protocolos y montajes ensayados. La aplicación está destinada a ejecución local en `127.0.0.1`.

El firmware se distribuye con las condiciones indicadas en [atribuciones](TERCEROS.md). Datos, modelos entrenados, capturas y bases de datos se obtienen o generan por los flujos documentados y se almacenan localmente.
