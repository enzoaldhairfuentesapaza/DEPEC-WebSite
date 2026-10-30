# v0.4.8 — imágenes sin botón visible

Se oculta el botón de ampliación que aparecía sobre las imágenes. El clic en la fotografía o afiche sigue abriendo el visor. El control accesible mediante teclado se conserva sin dibujar un botón sobre la foto; al enfocarlo se señala la imagen.

Copia esta entrega conservando `instance`, `.venv` y `.git`, ejecuta `iniciar.bat` y recarga con Ctrl+F5. No hay cambios en datos, dependencias ni otras funciones. Para una actualización mínima bastan `app/static/viewer-contact.css` y `app/templates/base.html`.

Se ejecutó la comprobación funcional existente del visor en DOM simulado. Este ajuste de CSS no cambia el código del servidor.
