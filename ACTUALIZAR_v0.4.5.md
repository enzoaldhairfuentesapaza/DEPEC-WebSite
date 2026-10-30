# v0.4.5 — collage y portada de DEPEC

## Actualizar

Detén el servidor, copia esta entrega sobre el proyecto y conserva `instance`, `.venv`, `.git` y tus respaldos. Ejecuta `iniciar.bat` y recarga con Ctrl+F5. No necesitas nuevas dependencias, borrar datos ni ejecutar `init-db`.

## Collage de eventos

- Cuatro columnas en escritorio, dos en tablet y una en móvil estrecho.
- Se mantienen como máximo seis eventos reales, ordenados por fecha en el documento.
- Las tarjetas verticales ocupan una columna y dos filas; las horizontales, dos columnas y una fila. En móvil estrecho las horizontales ocupan el ancho disponible manteniendo su formato horizontal.
- Se calcula la colocación para cada ancho antes de renderizar: los huecos se cubren con ilustraciones predeterminadas del sistema. Estos rellenos son decorativos, no se enlazan, no incluyen fechas y no se cuentan como eventos. No sustituyen los eventos sin imagen, que conservan su tarjeta solo con información.
- Los eventos publicados por DEPEC tienen contorno y etiqueta dorados en el collage general. Las tarjetas de las SEC/GJ mantienen su color de iglesia. El dorado no se aplica a las páginas individuales.
- Si todavía no hay eventos próximos, permanece el mensaje de calendario pendiente; no se fabrica un collage de supuestas actividades.

## Portada DEPEC

El encabezado de la directiva es **DIRECTIVA DEPEC**. Las páginas de iglesias conservan su encabezado anterior y su propia directiva.

La sección «Esta es nuestra familia» aparece solo en las páginas de SEC/GJ. Los perfiles de miembros y sus datos siguen guardados; no se copian al mural de DEPEC ni se eliminan.

Los mensajes de miembros aprobados se presentan en un collage de notas bajo «Voces de nuestras iglesias». Cada nota muestra autor, iglesia con su color y verificación. Se mantiene la revisión de cada mensaje: tener un perfil aprobado no publica automáticamente su contenido como testimonio. El límite existente es de doce mensajes recientes. En las páginas individuales se muestran solo los mensajes de su iglesia.

El calendario de cumpleaños y las demás secciones conservan su comportamiento.

## Verificación

Se comprueban todas las combinaciones de orientación para uno a seis eventos en cuatro, dos y una columnas: las tarjetas y rellenos cubren exactamente su rectángulo, sin solapamientos ni celdas vacías. También se comprueban el límite de eventos, el alcance del borde dorado, los encabezados por página, la ausencia del directorio en DEPEC y la aprobación y atribución de mensajes.

Las vistas estáticas están en `preview/index.html` y `preview/jorge-chavez.html`; los calendarios y formularios completos funcionan al iniciar Flask. La instalación del navegador de pruebas no estuvo disponible en este entorno: queda pendiente la revisión visual en tu navegador.
