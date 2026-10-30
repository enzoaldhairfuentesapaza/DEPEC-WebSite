# v0.4.4 — DEPEC, mapas y cumpleaños

## Actualizar

Detén el servidor y copia esta entrega sobre el proyecto. Conserva `instance`, `.venv`, `.git` y tus respaldos. Ejecuta `iniciar.bat` y recarga con Ctrl+F5. No borres la base ni ejecutes `init-db`. Se añaden dos columnas opcionales al perfil sin publicar los cumpleaños de los miembros existentes. No hay nuevas dependencias.

## DEPEC no tiene local

La portada de DEPEC ya no muestra la sección Nuestro local ni un mapa. Identidad y local y Organización omiten sus campos de iglesia, dirección y horario. Los eventos organizados por DEPEC tienen su propia sede; si no se especifica, aparece Sede por confirmar. Se limpian los locales ficticios exactos introducidos por la demo anterior; no se sustituyen las sedes reales de eventos existentes.

## Mapa de Jorge Chávez y otras iglesias

El bloqueo de la captura se debía a la política `Content-Security-Policy`: `default-src 'self'` también impedía los iframes externos. Se añade una directiva `frame-src` restringida a los dominios de Google Maps. Se mantienen las otras restricciones. También se permite `blob:` únicamente para imágenes, necesario para la vista previa local de los archivos seleccionados.

El enlace de Jorge Chávez sigue siendo `https://maps.app.goo.gl/KSo2PasAcs3HdyU36`. Al iniciar, el sistema intenta resolver enlaces cortos de iglesias que aún no tengan mapa exacto. Si Google devuelve las coordenadas del lugar, se guarda el mapa insertado correspondiente. No se confunden las coordenadas del centro de la cámara con las del lugar. Un fallo de red no impide iniciar el sistema y se limita a un intento automático por enlace y día. No se modifica el enlace original.

Puedes reintentar desde **Identidad y local → Actualizar mapa desde mi enlace**. La acción exige permisos de la iglesia y CSRF. También puedes pegar el código de **Google Maps → Compartir → Insertar un mapa**. Se aceptan solo URLs HTTPS de Google; las redirecciones a otros dominios se rechazan. Los enlaces cortos y los mapas necesitan conexión a Internet.

Si la resolución no está disponible y aún no hay una dirección confirmada, se conserva una vista referencial identificada como tal junto al botón de la ubicación compartida. En el entorno de desarrollo no se pudo resolver el enlace real de Jorge Chávez: no se inventaron coordenadas ni se afirma que ese servicio externo se haya verificado. La carga real del mapa debe comprobarse al iniciar en tu equipo.

## Directiva, miembros y testimonios

Insignias SVG centradas: corona para presidencia, estrella de reconocimiento para vicepresidencia, libreta para secretaría, moneda para tesorería, diálogo para vocalía y libro para asesoría. Los cargos pro muestran un símbolo de apoyo adicional. Cada cargo tiene acentos de color, forma y borde propios; las tarjetas centran también sus textos. Se conserva la fila compacta de la directiva y el desplazamiento cuando no cabe completa.

Los miembros usan avatares circulares más pequeños y cuatro columnas en escritorio. Versículos, gustos, dones y mensajes largos se amplían desde la tarjeta. Los testimonios reducen espacio y tipografía; los textos largos conservan una opción para leer el mensaje completo. Se mantienen temas claro y oscuro y los colores de cada iglesia.

## Calendario de cumpleaños

- **Público:** enlace Cumpleaños en el menú, acceso desde cada portada y ruta `/cumpleanos`. DEPEC reúne las iglesias y cada iglesia filtra su comunidad. Tiene meses anterior/siguiente, Hoy, filtro por iglesia, cuadrícula y lista del mes. No mezcla eventos.
- **Privado:** entrada Cumpleaños del panel y ruta `/birthdays`. Ahora usa una cuadrícula mensual y una lista; solo consulta los miembros del padrón a los que el líder tiene acceso.
- **Autorización:** en Mi perfil, el miembro selecciona día y mes y marca que desea compartirlo. Debe tener membresía aprobada, cuenta activa y perfil público aprobado. Guardar cambios vuelve a enviar el perfil a revisión. Retirar la autorización lo oculta inmediatamente.
- No se solicita ni publica año de nacimiento ni edad en el calendario público. El campo anterior «Compartir cumpleaños en panel interno» no equivale a autorización pública.
- El 29 de febrero se conserva: en años no bisiestos figura en la lista de febrero con una explicación, sin trasladar la fecha silenciosamente.
- Los perfiles ficticios de la demo reciben ejemplos de cumpleaños identificados como DEMO una sola vez. Los miembros reales no se publican automáticamente.

## Comprobaciones

Se prueban la ausencia de local DEPEC, la sede por evento, la política de marcos e imágenes, resolución de enlaces y rechazo de destinos externos, caché de errores de red, permisos de actualización del mapa, autorización y revisión de cumpleaños, separación entre iglesias, calendario privado y años bisiestos. Las coordenadas usadas en pruebas de resolución son ficticias; no se asignan al mapa real de Jorge Chávez.

Las vistas estáticas se regeneran con `python generar_vista_previa.py`. El calendario interactivo completo requiere iniciar Flask. No se dispone de navegador instalado en el entorno de verificación; falta una revisión visual en el navegador del usuario.
