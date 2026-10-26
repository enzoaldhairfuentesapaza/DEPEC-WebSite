# Actualizar el diseño a v0.2

Esta entrega modifica la presentación pública; no cambia el esquema de la base de datos, las cuentas ni los permisos.

1. Detén el servidor con Ctrl+C.
2. Copia el contenido de la carpeta `depec` del ZIP sobre tu proyecto existente. El ZIP no contiene `instance/`, `.venv/`, `.git/` ni `backups/`; conserva esas carpetas de tu instalación.
3. Los archivos principales actualizados son:
   - `app/templates/public.html`
   - `app/templates/base.html`
   - `app/static/public.css` (nuevo)
   - `app/static/app.js`
   - `app/static/images/` (tres imágenes nuevas)
   - README y documentación de la actualización.
4. Ejecuta tu `iniciar.bat` habitual y abre http://127.0.0.1:5000.
5. Si ves el diseño anterior, recarga con Ctrl+F5.

No ejecutes seed-demo sobre tus datos ni elimines la base de datos para actualizar el diseño.

## Cambios para el público

- Menú con Inicio, Eventos, Nuestros grupos, Calendario y Acceso de líderes.
- Mensaje de bienvenida, fotografía de portada y dos acciones principales.
- Accesos rápidos a eventos, grupos y calendario.
- Próximos eventos ordenados, excluyendo cancelados y realizados, con fecha, hora, lugar y detalles desplegables.
- Selección de SEC, GJ o todos los grupos, con estados accesibles y resultado anunciado a lectores de pantalla.
- Página por grupo con iglesia, dirección y horario, cuando estén registrados.
- Presentación de la comunidad, noticias, galería y respuestas a preguntas frecuentes.
- Pie de página con enlaces de ayuda y navegación.
- Menú para celular con control de apertura, cierre con Escape y navegación por teclado.
- Sin JavaScript, los grupos y el menú siguen visibles y los detalles funcionan con HTML nativo.
- Contempla reducción de movimiento según las preferencias del dispositivo.

## Fotografías de ejemplo

Las tres imágenes de `app/static/images/` fueron generadas con IA. Son escenas ficticias: encuentro, integración y servicio comunitario. La portada y los ejemplos de la galería lo indican. Un evento sin afiche muestra una imagen marcada como referencia; si subes un afiche, se utiliza ese archivo. Las fotografías de ejemplo pueden reemplazarse conservando sus nombres de archivo.

Al existir fotografías públicas en Galería, se muestran esas fotografías en lugar de los ejemplos. La sección informativa conserva su imagen ilustrativa identificada.

## Subir esta actualización a GitHub

Dentro de tu carpeta del proyecto, después de copiar y probar:

```powershell
git status
git add app README.md ACTUALIZAR_v0.2.md docs
git commit -m "Mejora portada DEPEC, navegación pública e imágenes de referencia"
git push origin main
```

Opcionalmente, si aún no existe esa etiqueta:

```powershell
git tag -a v0.2.0 -m "Rediseño de la experiencia pública DEPEC"
git push origin v0.2.0
```

Los comandos no crean ni modifican el repositorio remoto por sí solos durante esta entrega; ejecútalos en tu copia que ya está conectada con GitHub.

## Verificación

Se comprobó el renderizado de la portada, páginas SEC/GJ, calendario y acceso; las referencias de imágenes, estilos y enlaces internos responden correctamente. También se ejecutó la suite de regresión del sistema. La apariencia en un navegador de escritorio o celular necesita revisión en tu instalación: el navegador remoto disponible no comparte el acceso al servidor local.
