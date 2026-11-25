# Protocolo del piloto Few-Shot con ESP32-C6

25 de noviembre de 2026. Evaluación descriptiva del mismo investigador en el salón parcialmente ocupado. Se mantiene el montaje del diagnóstico previo, con TX al suroeste a unos 40 cm, RX al norte a unos 60 cm, 1,20 m de separación, canal 11 y el firmware instalado. La postura de quietud es sentada. La caminata es de ida y vuelta por un tramo de unos 4 m paralelo al enlace, sin cruzarlo. Se anotan cambios y movimientos ajenos observados, sin asignar actividades a terceros.

## Grabaciones y controles

- Cuatro soportes nuevos, dos por actividad, y cuatro consultas nuevas, dos por actividad. Sesiones de 60 s, identificadas por rol, actividad, repetición y hora UTC antes de capturar. Orden previsto por rol: quietud 1, caminata 1, quietud 2, caminata 2. El operador confirma cada toma y conserva las mismas condiciones en lo posible.
- Se preservan los archivos crudos y sus SHA-256. Las cuatro tomas del diagnóstico quedan como evidencia exploratoria y están excluidas de este experimento. Cada grabación nueva aporta datos a un solo rol. La etiqueta de referencia procede de la actividad declarada por el operador.
- Se usa el extractor histórico `features()`, con recepción de al menos 60 paquetes/s, hasta 10 % de saltos nominales y hasta 1 % de filas malformadas. Las ventanas válidas duran un segundo, excluyen los extremos como en el método histórico, contienen al menos 60 registros y tienen un hueco interno máximo de 100 ms. La función requiere un mínimo de tres ventanas por sesión. Se comprueban el canal 11 y el vector CSI de 256 enteros. Una toma que falle estos controles se conserva como incidencia y se coordina otra del mismo rol. Los criterios no dependen de las predicciones.

## Comparación fijada antes de evaluar consultas

Se mantiene la copia congelada `binario.npz`, SHA-256 `1834cd62268f8da966eb409975865827dfb9bae28279085209d3adba3f178cc7`, con las seis características, normalización de origen y distancia euclídea cuadrática del modelo. Se comparan tres métodos sobre las mismas ventanas y grabaciones de consulta.

1. **Histórico 0-shot.** Se mantienen los centros de origen.
2. **Prototipos destino.** Para cada actividad, se promedian las `K` ventanas de soporte en las coordenadas normalizadas del modelo de origen.
3. **Prototipos regularizados.** Para cada clase se usa `(K × centro_destino + centro_origen) / (K + 1)`. Se fija el peso del origen en una ventana equivalente, para que su influencia disminuya al crecer `K`. Es una condición predefinida del piloto, sin búsqueda de pesos en las consultas.

Se evalúan `K = 1, 5, 10` ventanas etiquetadas por clase, con dos asignaciones espejadas de las dos grabaciones de soporte de cada clase. Se asignan `ceil(K/2)` ventanas al primer soporte y `floor(K/2)` al segundo, invirtiendo estos papeles en la otra asignación. Una grabación aporta sus ventanas en un orden fijo: primero la elegible más cercana al punto medio de la toma y luego, en cada paso, la que maximiza la distancia temporal mínima respecto de las ya seleccionadas. Los empates se resuelven con el inicio más temprano. Así, los soportes de cada asignación son anidados por presupuesto. Un presupuesto se omite si alguna grabación carece de ventanas suficientes para sus dos asignaciones. Se guardan los identificadores y tiempos de todas las ventanas seleccionadas.

Se publican exactitud, precisión y recall por clase y macro, Macro-F1, matrices de confusión y diferencias de exactitud y Macro-F1 frente a 0-shot. Se conservan predicciones individuales y mayorías de sesión, con métricas por ambos niveles. En empates de mayoría se usa el orden histórico de clases, quietud antes de caminata. Las diferencias se calculan por asignación sobre las mismas consultas y se muestra también la media descriptiva de ambas asignaciones. Las ventanas de una sesión y las dos asignaciones de soporte son dependientes. El número de adquisiciones se informa por rol y clase.

La comparación con la CNN pública de S5/S6/S7 se cierra en el análisis de compatibilidad ya documentado. Este piloto conserva el modelo binario y la representación del ESP32-C6. Sus resultados se registran como evidencia complementaria, aparte de las transferencias principales de la tesis.
