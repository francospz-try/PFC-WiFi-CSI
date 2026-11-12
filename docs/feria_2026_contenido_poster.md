# Contenido base del póster — PFC Wi-Fi CSI

## Título
Reconocimiento piloto de quietud y caminata mediante Wi-Fi CSI con dos ESP32-C6.

## Problema
Las señales Wi-Fi cambian al interactuar con el cuerpo y el entorno. Se explora si esas variaciones permiten distinguir actividades sin imágenes de cámara.

## Objetivo
Implementar adquisición reproducible de CSI y evaluar un clasificador local de quietud frente a caminata, documentando sus errores y límites.

## Solución implementada
Dos ESP32-C6 transmiten y reciben por ESP-NOW. Python almacena y procesa el CSI —información del estado del canal inalámbrico— y una aplicación Django permite revisar capturas y ejecutar HAR —reconocimiento de actividades humanas— sobre grabaciones.

## Cómo funciona y arquitectura
Transmisor → enlace inalámbrico → receptor → USB → adquisición Python → seis indicadores temporales → clasificador por prototipos → aplicación web. Las ventanas se asignan al prototipo más próximo y la grabación se resume por mayoría.

## Tecnologías
ESP32-C6, ESP-NOW, Python, NumPy, Matplotlib y Django. No se utilizan imágenes del usuario para clasificar.

## Metodología experimental
Una habitación; separación TX-RX 1,2 m y alturas 0,8/0,4 m. Seis grabaciones de aprendizaje: tres quietud y tres caminata. Evaluación interna por grabaciones completas: cuatro para ajuste y dos reservadas. Después, reajuste con las seis y dos ensayos nuevos independientes del ajuste. Todas las grabaciones duraron aproximadamente 60 s; 55 ventanas utilizables por grabación.

## Resultados reales
Evaluación interna: 68,18% de ventanas correctas; F1 macro 0,6797. Matriz quietud/caminar: [[33,22],[13,42]]. En dos ensayos nuevos, la mayoría identifica correctamente ambas actividades. Caminar: 47/55 ventanas (85,45%); quietud: 33/55 (60%). Conjunto nuevo: 72,73% de ventanas correctas; F1 macro 0,7228. Son proporciones de ventanas, no probabilidades de confianza.

## Limitaciones
Ocho grabaciones de una campaña local no prueban generalización. Las ventanas contiguas están correlacionadas. Quietud se confunde con caminar en el 40% de las ventanas de la prueba nueva. No existe todavía reconocimiento continuo validado, conteo de personas ni detección certificada de presencia. Few-Shot con datos externos es una línea experimental distinta y no está demostrado con estos ESP32.

## Conclusiones
Se verificó una cadena funcional de adquisición y clasificación local, con datos originales íntegros y resultados reproducibles. La clasificación por mayoría es útil para una demostración controlada, pero oculta errores temporales que deben reducirse y evaluarse con más sesiones.

## Trabajo futuro
Recopilar repeticiones independientes, controlar montaje y actividades, comparar mejoras simples sin contaminar la prueba final y validar después una implementación continua que detecte explícitamente ausencia de datos.

## Evidencias visuales sugeridas
Priorizar arquitectura, comparación CSI, matriz interna, proporciones nuevas y fotografía real del montaje. La comparación visual de señales describe variaciones: por sí sola no demuestra reconocimiento. Presentar la aplicación como demostración mediante grabaciones reales previamente adquiridas; no como predicción en vivo.
