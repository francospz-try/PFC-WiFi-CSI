# PFC — Sesión 7

Base recuperada de PFC_WiFi_CSI_Practica07_Integrada_Final.zip.

## Iniciar
Doble clic en INICIAR.cmd. En el primer inicio se solicita crear tu administrador. Abrir http://127.0.0.1:8000/login/. En /admin/ puedes crear investigadores (sin permisos de staff). La clave privada se conserva localmente en .django-secret; no compartir ese archivo.

En la web: crear experimento con S5 y S7 DEMO, ejecutar demostración y descargar CSV. Las métricas sintéticas solo validan el software. PROBAR.cmd ejecuta las pruebas.

## Al terminar las descargas
No copiar datasets si falta espacio: inventariar directamente en su ubicación o disco externo. Desde PowerShell, dentro de esta carpeta:

```powershell
.\.venv\Scripts\python.exe cli.py inventario "D:\ruta\S5.zip" --salida outputs/inventario_S5.json
.\.venv\Scripts\python.exe cli.py inspeccionar "D:\ruta\S5a_A.mat"
```

Antes de preparar: confirmar csi_buff, eje temporal y organización de antenas con los archivos reales. El lector actual procesa MAT clásico; MAT v7.3 se inspecciona pero necesita adaptar lectura HDF5. No asumir el eje temporal ni ejecutar preparación mientras la descarga esté incompleta.

Tras auditoría, el comando `cli.py preparar --help` muestra los parámetros. Generar S5.npz y S7.npz con idéntico receptor, antena y preprocesamiento en datos_locales. Ejecutar:

```powershell
.\.venv\Scripts\python.exe cli.py experimento --origen datos_locales/S5.npz --destino datos_locales/S7.npz --salida outputs/S5_S7 --semilla 42
```

Entrega CSV de métricas, matrices de confusión y protocolo JSON. Comparación 0/1/5/10 con consulta fija y soporte disjunto. Son bloques de una grabación por clase, no sesiones independientes. Esta fase requiere validar datos y protocolo antes de informar resultados científicos.

## Alcance instalado
Login, administrador/investigador, catálogo, experimentos propios, demostración y exportación. Datos reales por CLI. Captura ESP32 e integración web de entrenamiento real pendientes; no se simulan como funciones completadas.
