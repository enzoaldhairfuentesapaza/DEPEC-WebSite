# Arquitectura y decisiones

Flask recibe cada solicitud, carga al usuario activo desde SQLite, valida el token CSRF en operaciones POST, verifica el alcance y renderiza HTML con Jinja. JavaScript solo mejora la interfaz; no determina los permisos. Los archivos se guardan fuera de `static/` y se entregan mediante rutas controladas.

## Datos

- `groups`: DEPEC tiene id 1 estable; las demás organizaciones son SEC/GJ.
- `users`: cuentas, hashes de contraseña y estado de acceso.
- `assignments`: cargos, periodos y estado activo/histórico.
- `grants`: permisos adicionales de lectura o edición por módulo y organización.
- `records`: módulo, organización, autor, fechas y datos JSON validados por el formulario del módulo.
- `participation`: relación de un evento/reunión con miembros del grupo anfitrión.
- `audit`: acciones del usuario, organización y fecha.
- `attempts`: intentos de acceso fallidos para limitar ataques de contraseña.

El JSON permite ampliar formularios rápidamente en el prototipo. Para producción conviene migrar eventos, miembros, movimientos y documentos a tablas propias con restricciones, versiones y migraciones; evaluar PostgreSQL cuando exista concurrencia significativa. Los importes se validan con Decimal y se guardan como texto decimal con dos cifras; no se suman con float en el servidor.

## Acceso

El permiso se calcula a partir del usuario activo, sus cargos activos y permisos adicionales activos. Una asignación DEPEC habilita su alcance en todos los grupos. Cada formulario, descarga, exportación y operación de escritura comprueba acceso en el servidor. La edición no permite mover registros cambiando group_id. El traslado entre grupos necesita un flujo específico futuro.

El administrador puede gestionar todas las organizaciones. Presidencia/vicepresidencia supervisa todo dentro de su alcance. Secretaría administra el padrón y documentos. Tesorería administra movimientos. Los vocales leen actividades por defecto; permisos adicionales permiten delegar publicaciones y otras secciones.

Los eventos públicos se muestran según visibilidad. Las publicaciones públicas exigen estado Publicado y fecha alcanzada. La galería pública exige Publicado. Los archivos públicos son imágenes de eventos/publicaciones/galería expresamente públicos; los documentos y comprobantes nunca usan esa ruta. Las imágenes verifican extensión y cabecera PNG/JPEG; los documentos se entregan como descarga. Para producción hace falta inspección más profunda de archivos y límites de almacenamiento.

## Controles incluidos

Contraseñas con hash de Werkzeug, CSRF, cookies HttpOnly/SameSite, sesiones de ocho horas, validación de formulario, SQL parametrizado, escapado HTML, nombres de archivo aleatorios, límite de carga de 10 MB, encabezados de protección, prevención de fórmulas en CSV y limitación de intentos por correo. Las respuestas autenticadas deshabilitan caché.

Las fechas se almacenan sin zona horaria en formato ISO; usa un servidor configurado en America/Lima. Un despliegue con usuarios de diferentes zonas requerirá normalizar fechas y definir la zona de cada evento. La interfaz funciona sin recursos de terceros.

## Operación futura

El servidor `run.py` es para desarrollo local. Para un servidor Python puede usarse Waitress, incluido en requirements: `python -m waitress --listen=127.0.0.1:8000 run:app`, detrás de un proxy con HTTPS. Configura COOKIE_SECURE=1 solo con HTTPS y gestiona SECRET_KEY fuera del repositorio. Esta instrucción no implica que el sistema esté desplegado ni endurecido para producción.

Necesita una estrategia de migraciones, copias programadas, prueba real de restauración, monitoreo, revisión de permisos, manejo de errores y auditoría de seguridad. Las copias deben proteger SQLite y adjuntos conjuntamente. No se incluye envío de correo, WhatsApp ni servicios externos.
