# Plan de auditoría HAR y evidencias — 2026-11-12

Objetivo: auditar el modelo operativo sin sobrescribirlo, corregir defectos demostrados y preparar evidencias reales reproducibles. Especificación: las dos solicitudes completas entregadas por el operador en esta conversación.

Diseño: conservar adquisición, seis indicadores y prototipos existentes. Separar evaluación interna (modelo ajustado con cuatro sesiones), modelo operativo (seis sesiones) y dos pruebas nuevas. Exportar resultados derivados en outputs/feria_2026, documentación y scripts apropiados a Git. No implementar directo ni póster definitivo. Se trabaja en la rama expresamente autorizada, sin worktree alternativo porque los datos privados y el modelo operativo están aquí.

- [x] Registrar HEAD, estado, hashes y ejecutar suites iniciales.
- [x] Reconstruir calidad, ventanas, evaluación interna y dos inferencias; exportar trazabilidad y análisis de errores con fuentes reales.
- [x] Reproducir mediante pruebas temporales los defectos de selección, propósito y configuración; aplicar cambios localizados y verificar.
- [x] Generar figuras SVG/PNG y capturas de una instancia local aislada con datos reales; identificar evidencias pendientes sin inventarlas.
- [x] Crear diagnóstico, handoff autocontenido, contenido del póster, guía de fotografías, demostración e inventario.
- [x] Ejecutar suites finales, revisión independiente, integridad final, diff y exclusiones; commits separados y push de desarrollo/csi-captura-estable.

Foco de revisión: captura reservada con etiqueta no debe entrenar; selector y resultado deben concordar incluso tras error; preferencias no reutilizan actividad/propósito; modelos históricos sin fecha explícita no deben inventarla; ninguna inferencia modifica raw/modelos.

Progreso: HEAD inicial 95358a6873f90c5de308304b1b8accf1a7bd0dfd; árbol limpio; pytest inicial 26 aprobadas. Auditoría numérica y preparación de servidor delegadas en dominios independientes según guía de trabajo paralelo. Correcciones esperan suite Django inicial.

Cierre: auditoría numérica reproducida dos veces; 20 originales íntegros; 30 pytest y 32 Django (1 omitida); revisión independiente sin bloqueos. Pendiente menor: selección borrada manualmente devuelve 404. Evidencias: siete capturas y siete figuras en dos formatos. Publicación de la rama autorizada como último paso.
