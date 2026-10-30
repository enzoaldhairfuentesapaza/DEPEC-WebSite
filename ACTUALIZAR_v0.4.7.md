# v0.4.7 — destacados DEPEC, colores y álbumes

## Actualizar

Detén el servidor y copia esta entrega sobre tu proyecto. Conserva `instance`, `.venv`, `.git` y tus respaldos. Ejecuta `iniciar.bat` y recarga con Ctrl+F5. No ejecutes `init-db` ni borres la base de datos. No se requieren nuevas dependencias o columnas.

## Rellenos y destacados del collage

Los huecos verticales y cuadrados usan ilustraciones SVG con composición específica: textos centrados y distribuidos en varias líneas. Se muestran completas, sin ampliar una imagen horizontal hasta cortar sus letras. Los rellenos horizontales conservan sus imágenes anteriores.

En la portada DEPEC, los eventos publicados por DEPEC se reconocen por un marco más grueso, sombra de su color y cabecera completa con «DEPEC · ORGANIZA». Se elimina el tratamiento dorado. No se cambia automáticamente el rojo configurado; el destacado utiliza el color vigente de DEPEC. Se mantienen las cuatro columnas, la adaptación a pantallas pequeñas y el límite de seis eventos.

## Colores de las iglesias

Los administradores y usuarios con un cargo activo en DEPEC pueden abrir **Panel → Colores de las iglesias**. Cada formulario guarda únicamente el color de la organización correspondiente y registra la modificación en el historial.

El color se refleja en la identidad de la página, sus eventos, etiquetas, calendarios y contacto. Los líderes de iglesias siguen editando sus textos, fotos y local; su color queda administrado por DEPEC. No basta con enviar un campo oculto desde otro formulario para cambiarlo. Las demás atribuciones de los cargos no se amplían.

## Eventos pasados

Se elimina por completo de las portadas el bloque «Ya compartimos estos momentos». No se borran los eventos ni su historia. En el calendario, navega al mes correspondiente y selecciona el evento: seguirá apareciendo con estado Finalizado cuando haya pasado su cierre.

## Álbumes con página propia

Cada portada muestra como máximo **tres álbumes públicos recientes**, con el botón **Ver todos los álbumes**. El menú Álbumes también abre el directorio.

El directorio `/albumes` permite seleccionar DEPEC o una iglesia, buscar por título o descripción y recorrer **12 álbumes por página**, ordenados del más reciente al más antiguo. La búsqueda admite diferencias de mayúsculas y tildes; los símbolos `%` y `_` se buscan literalmente. La página recuerda comunidad y búsqueda al cambiar de página.

Por defecto, la portada DEPEC y su directorio muestran álbumes creados por DEPEC; una SEC/GJ muestra los suyos. El selector permite visitar otra comunidad. Los álbumes internos y las fotos privadas, en borrador o no publicadas no se muestran ni se cuentan como imágenes públicas, incluso si un administrador abre el directorio público.

Solo se cargan las tarjetas de la página solicitada y se consultan su portada y cantidad de fotografías sin cargar todas las imágenes de todos los álbumes. El visor de imágenes y la burbuja de contacto siguen disponibles en el directorio.

## Comprobaciones

Se comprueban composiciones de relleno por orientación, conservación de eventos pasados en el calendario, límite de tres álbumes en portadas, paginación, búsqueda sin tildes y sensible a símbolos literales, separación de comunidades, conteo de fotos públicas y permisos para gestionar colores. Se conserva la prueba de cobertura de todas las combinaciones del collage sin huecos ni solapamientos.

Las vistas estáticas se regeneran con `python generar_vista_previa.py`. La comprobación de interacción del visor se ejecuta en un DOM simulado; sigue pendiente la revisión visual final en un navegador real.
