# Datos reales — 21/10/2026

Se leen S5.zip, S6.zip y S7.zip directamente de Descargas; no se extraen ni se modifican. Tamaño total de sus contenidos: 38.092.565.748 bytes (38,09 GB decimales).

## Uso en la web
1. Si estaba abierta, detener la aplicación con Ctrl+C y volver a abrir INICIAR.cmd.
2. Iniciar sesión con tu cuenta habitual.
3. Crear experimento seleccionando dos datasets **CSI REAL** de ambientes distintos.
4. Abrir el detalle y pulsar **Ejecutar CSI real · 0/1/5/10-shot**.
5. Consultar las métricas y exportar CSV. El botón DEMO continúa generando datos artificiales; la naturaleza del resultado identifica la última operación ejecutada.

Los datasets DEMO y CSI REAL son entradas distintas. Los usuarios investigadores solo pueden acceder a sus experimentos; los administradores pueden verlos todos.

## Protocolo
- Fuente: Exposing the CSI; README y licencia dentro de los ZIP originales.
- Ambientes: S5 laboratorio, S6 oficina, S7 vestíbulo. Participante 1, día 2, según README.
- Actividades A/B/C/G/K: caminar, correr, saltar, agitar manos y sentadillas.
- Receptor a; antena 0 seleccionada en el tercer eje. No se diezma el eje temporal: las antenas ya están separadas.
- Variable real: csi [12000, 2048, 4], complex double.
- Ventanas no superpuestas de 128 paquetes (aprox. 0,853 s a 150 Hz documentados), 8 grupos de subportadoras, 24 características de amplitud.
- Sin procesamiento Doppler/SHARP, ni selección especializada de subportadoras activas. Baseline exploratorio.
- Normalización ajustada únicamente al origen; regresión logística; prototipos destino mezclados con probabilidad base, peso fijo 0,5.
- Consulta común para 0/1/5/10; primeras 10 ventanas por clase reservadas como soporte y 4 de purga. Soportes anidados por semilla 42.
- Una sola grabación por actividad: las ventanas no son sesiones independientes y los resultados no prueban generalización a otras personas, días o dispositivos.

## Archivos
- datos_locales/S5_real.npz (y S6/S7): características compactas.
- datos_locales/S5_real.json (y S6/S7): estructura, CRC de miembros ZIP y configuración.
- outputs/reales/ORIGEN_DESTINO/: seis comparaciones, métricas, matrices y protocolo.
- outputs/web/experimento_ID_real/: resultados ejecutados desde la web.

Para regenerar desde esta carpeta:
```
.venv\Scripts\python.exe preparar_reales.py
```
Este comando vuelve a leer unos 5,32 GB de miembros seleccionados sin extraerlos; carga un MAT a la vez. Los NPZ son mucho menores y bastan para volver a ejecutar el baseline. No borres los ZIP: son los originales.

El comando antiguo `cli.py preparar` corresponde al formato legacy csi_buff. Para estos ZIP utiliza preparar_reales.py, que valida csi y selecciona antenas en el eje correcto.
