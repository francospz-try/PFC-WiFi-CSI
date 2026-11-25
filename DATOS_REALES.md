# Experimentos con CSI público

Obtén `S5.zip`, `S6.zip` y `S7.zip` desde los [depósitos de Exposing the CSI](https://github.com/ansresearch/exposing-the-csi) o usa copias locales verificadas. Coloca los tres ZIP en el mismo directorio. La preparación lee miembros de los ZIP sin extraerlos ni modificarlos.

## Preparar y registrar

Desde la raíz del repositorio indica el directorio de los ZIP. El argumento `--descargas` admite cualquier directorio.
```powershell
$csi = 'ruta\a\los\archivos'
.\.venv\Scripts\python.exe preparar_reales.py --descargas $csi
```

El script escribe `S5_real.npz`, `S6_real.npz`, `S7_real.npz` y sus JSON en `datos_locales/`. Si ya cuentas con esos seis derivados verificados de la misma configuración, puedes copiarlos a esa carpeta. Arranca el portal una vez para crear la clave, aplicar las migraciones y crear tu cuenta. Registra los tres datasets desde otra terminal PowerShell.

```powershell
$env:DJANGO_SECRET_KEY = (Get-Content '.django-secret' -Raw).Trim()
.\.venv\Scripts\python.exe web_local/manage.py registrar_reales
```

En el portal crea un experimento con dos datasets **CSI REAL** de ambientes distintos. Pulsa **Ejecutar CSI real · 0/1/5/10-shot**, compara las dos tablas, abre matrices de confusión y exporta el CSV. El catálogo distingue las entradas artificiales de las mediciones.

## Protocolo y archivos

- S5 laboratorio, S6 oficina y S7 vestíbulo, participante A y día 2 según los autores. Actividades A/B/C/G/K, caminar, correr, saltar, agitar manos y sentadillas.
- Receptor a, antena 0. El MAT contiene `csi[12000,2048,4]` complejo. Ventanas de 128 paquetes sin solapamiento, ocho grupos espectrales y 24 características de amplitud. A 150 Hz documentados, la duración nominal es 0,853 s.
- Escalador ajustado con origen. La regresión logística proporciona la base. El portal compara combinación de probabilidades con peso 0,5 y ajuste convencional de la cabeza logística.
- Consulta común para 0/1/5/10, primeras diez ventanas por clase reservadas como candidatas para soporte y cuatro de purga. Soportes anidados para cada semilla. Una grabación por actividad. Las ventanas de la misma grabación son dependientes.
- Los derivados incluyen características en NPZ y procedencia en JSON. Las salidas de la CLI están en `outputs/reales/`. Las nuevas ejecuciones web se guardan bajo `outputs/web/experimento_ID_ejecuciones/`. Las históricas sin identificador conservan `outputs/web/experimento_ID_real/`.
- El comando `cli.py preparar` conserva el formato histórico `csi_buff`. Para los ZIP de esta guía se usa `preparar_reales.py`.

## Auditoría de lectura

La vista **Demostración del avance** usa un inventario separado y los ZIP originales.
```powershell
.\.venv\Scripts\python.exe herramientas/auditar_publicos.py --archivos $csi
.\.venv\Scripts\python.exe herramientas/auditar_15_completos.py --archivos $csi
.\.venv\Scripts\python.exe herramientas/demo_entregable.py --archivos $csi --member S5/S5a_A.mat
```

Para ejecutar esa lectura desde la web, define `$env:PFC_PUBLIC_CSI_DIR = (Resolve-Path $csi).Path` antes de iniciar la aplicación. Si no configuras una ruta, el script busca los ZIP en `datos_locales/`. Los informes y ventanas de demostración se guardan bajo `outputs/`. La proyección espectral de esta vista sirve para inspeccionar la lectura y tiene alcance exploratorio.
