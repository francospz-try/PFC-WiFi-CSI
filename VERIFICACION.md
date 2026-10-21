# Verificación local — 20 de octubre de 2026

Python 3.12; entorno .venv instalado. Versiones exactas: requirements-lock.txt.

- Pruebas del núcleo: 8 aprobadas.
- Pruebas Django: 7 aprobadas, incluyendo demo completa, exportación, autorización por propietario y POST con CSRF.
- Django check: sin incidencias.
- Migraciones SQLite aplicadas.
- Catálogo DEMO S5/S7 creado.
- Demo CLI 0/1/5/10 ejecutada; archivos en outputs/demo_sintetica/resultados.

Primer inicio: INICIAR.cmd solicita crear administrador. No hay contraseñas predeterminadas. No se dejó servidor ejecutándose.

Pendiente: auditar archivos MAT descargados, confirmar ejes/antenas y ejecutar experimentos con señales reales. Las pruebas actuales usan datos artificiales. Captura ESP32 y entrenamiento real desde web aún no están implementados.
