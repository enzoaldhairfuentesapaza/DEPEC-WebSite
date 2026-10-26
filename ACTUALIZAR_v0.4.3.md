# v0.4.3 — eventos, directiva y mapa del local

## Actualización

Detén el servidor y copia esta entrega sobre tu proyecto. Conserva `instance`, `.venv`, `.git` y tus respaldos. Ejecuta `iniciar.bat` y recarga con Ctrl+F5. No ejecutes `init-db` sobre tu base existente. La columna del mapa se añade automáticamente sin eliminar datos. Se mantiene la reparación UTF-8 de v0.4.2.

## Tarjetas de eventos

En Eventos → Nuevo / Editar puedes seleccionar:

- **Formato automático**: imagen vertical → tarjeta vertical; imagen horizontal → tarjeta horizontal. Una imagen cuadrada se presenta en tarjeta vertical. Sin imagen, el formato automático es horizontal.
- **Vertical / Horizontal**: cambia el formato sin recortar el afiche.
- **Imagen propia**: PNG o JPG; al reemplazarla se detectan sus nuevas dimensiones.
- **Sin imagen**: solo la información, sin un bloque vacío para el afiche.
- **Imagen genérica**: Encuentro (vertical), Comunidad o Servicio (horizontales), ilustraciones SVG incluidas en el sistema.

La vista previa usa la tarjeta pública y cambia al editar nombre, iglesia, fecha, hora, local, estado, imagen y formato. La imagen seleccionada se lee en tu navegador; no se sube hasta Guardar. El collage ajusta su escala al ancho disponible, de modo que la vista previa muestra el formato y contenido, no una posición exacta dentro de los seis eventos. La vista previa en vivo necesita JavaScript.

Elegir una imagen genérica o Sin imagen conserva el archivo original para poder volver a Imagen propia; deja de mostrarse en la tarjeta y en el hero. No se borra la fotografía original ni su registro del catálogo de archivos.

El collage mantiene el límite de seis eventos y ahora ocupa como máximo 980 px (940 px en pantallas grandes). La orientación gobierna su distribución, en lugar de imponer formas por la posición de las tarjetas. Su contorno puede variar según la mezcla de formatos: no se deforma una tarjeta para forzar un cuadrado exacto. En móvil se conservan tarjetas verticales y horizontales legibles; las pantallas más estrechas usan tarjetas verticales centradas.

## Directiva y textos

La directiva principal se muestra en una fila de tarjetas compactas, con foto, nombre completo, cargo, mensaje y contacto autorizado. Si hay muchos vocales o poco ancho, se recorre horizontalmente, también con teclado al enfocar la fila. Los líderes adicionales permanecen debajo. No se ocultan cargos para limitar la fila.

Presidencia usa corona dorada; vicepresidencia, estrella; secretaría, pluma; tesorería, insignia tipo moneda; vocalía, estrella de servicio. Los cargos pro tienen insignias de apoyo con borde discontinuo. Se mantienen los colores de cada organización y los temas claro/oscuro. Se ajusta la escala de títulos, etiquetas, fechas y textos de apoyo.

## Mapa del local

Cada página muestra un mapa de Google Maps. Para fijar el punto exacto entra a **Identidad y local**:

1. Abre tu ubicación en Google Maps.
2. Selecciona **Compartir → Insertar un mapa → Copiar HTML**.
3. Pégalo en **Mapa insertado de Google Maps**. También se acepta el enlace `https://www.google.com/maps/embed?pb=...` del atributo `src`.
4. Guarda.

El sistema extrae únicamente el enlace del iframe y permite solo dominios y rutas de inserción de Google Maps. No ejecuta el HTML pegado. Cada iglesia gestiona su mapa dentro de sus permisos. El enlace corto existente sigue disponible para abrir la ubicación compartida.

Si no hay código de inserción, se usa la dirección configurada como búsqueda. Si falta una dirección confirmada o solo hay un enlace corto, se muestra Arequipa como vista referencial, identificada expresamente. No se inventan coordenadas para Jorge Chávez. El mapa depende de conexión a Internet y de que Google Maps pueda cargar en el navegador; no usa una clave API en esta versión.

## Verificación

Pruebas de orientación automática y manual, modos de imagen, conservación del archivo al ocultarlo, formulario con vista previa, aislamiento y validación del mapa, migración de bases anteriores y regresión del sistema. JavaScript comprobado sintácticamente. Las vistas estáticas se regeneran con `python generar_vista_previa.py`. El entorno de verificación no dispone de un navegador instalado: la interacción visual y la carga externa del mapa deben comprobarse al ejecutar el proyecto en tu equipo.
