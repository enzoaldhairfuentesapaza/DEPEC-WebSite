# Alcance del prototipo v0.1

El objetivo es probar los flujos principales de la propuesta y recoger feedback. No todas las ampliaciones de la conversación son funciones terminadas. Esta lista conserva el alcance completo para continuar el proyecto.

| Área | Estado actual | Ampliación pendiente |
|---|---|---|
| DEPEC y seis grupos | Implementado: directorio, fichas, colores, iglesia, dirección, horario y edición | Logos propios, contacto/redes configurables, activar/inactivar grupos desde interfaz |
| Página pública | Implementado: inicio, página por grupo, noticias, calendario y galería | Presentación institucional oficial, contacto y documentos públicos |
| Usuarios y directivas | Implementado: cuentas, cargos múltiples, varios vocales, periodos, historial, desactivación, permisos adicionales | Invitaciones por correo, vencimiento automático de cargos y recuperación de cuenta |
| Publicaciones | Implementado: CRUD, categorías, visibilidad, borrador, fecha futura y afiche | Flujo formal de aprobación, publicación fijada y múltiples adjuntos |
| Calendario y eventos | Implementado: mensual, colores, filtros, eventos de varios días, estados y afiche | Vistas semanal/lista, recurrencia, detección de cruces, múltiples organizadores, enlaces virtuales y exportación ICS |
| Miembros | Implementado: padrón privado, filtros de texto, bautismo, fechas, contacto, apoderado y exportación | Importación Excel/CSV, duplicados, traslados con historial y campos personalizados |
| Cumpleaños | Implementado: listado mensual privado e indicador de consentimiento | Calendario de cuadrícula, recordatorios, tarjetas y publicación consentida |
| Secretaría | Implementado: tipos documentales, archivos privados, periodos y estados | Historial de versiones de archivo, plantillas y documentos generados |
| Solicitudes | Implementado: registro individual por grupo, archivo de respuesta, vencimiento y estado | Solicitar a todos los grupos en una operación, revisión diferenciada y notificaciones |
| Tesorería | Implementado: ingresos/egresos PEN, categorías, comprobantes, cuentas y estado de aprobación | Cierres inmutables, doble aprobación, fondos por cuenta, conciliación, saldos por periodo y rendición formal |
| Presupuesto y plan | Implementado: actividades, objetivos, responsables, presupuesto, fechas y avance | Comparativo presupuesto/ejecución, evidencias y cierre anual automático |
| Reuniones | Implementado: agenda, acuerdos escritos, convocatoria y asistencia | Convocatorias enviadas, confirmaciones, acuerdos convertidos en tareas y acta generada |
| Inscripciones | Implementado: registro interno de miembros del grupo anfitrión con cupos | Registro público, invitados externos y participación entre grupos |
| Galería | Implementado: fotografía, descripción, fecha, borrador y visibilidad | Álbumes, carga múltiple, videos y moderación |
| Panel / alertas | Implementado: próximos eventos, tareas y entregas pendientes | Centro de notificaciones con leído/no leído, correo y enlaces WhatsApp |
| Reportes | Implementado: acumulados por organización, CSV e impresión a PDF | Filtros por periodos, gráficas, reportes de asistencia y PDF con formato institucional |
| Auditoría | Implementado: registro básico de acciones con usuario/fecha | Diferencias antes/después, retención y protección contra manipulación administrativa |
| Copias | Implementado: script manual con copia consistente de SQLite | Programación, cifrado y prueba de restauración automatizada |
| Interfaz | Implementado: diseño adaptable por CSS, menú móvil, navegación y estados vacíos | Verificación visual en navegador de escritorio/móvil y pruebas de accesibilidad completas |

## Orden sugerido de siguientes iteraciones

1. Validar matriz de permisos y aprobación con líderes DEPEC, secretaría y tesorería.
2. Separar entidades principales en tablas y añadir migraciones; preservar los datos creados en el piloto.
3. Implementar traslados, importación del padrón y solicitudes documentales masivas.
4. Añadir flujos de aprobación, versiones documentales y cierres de tesorería.
5. Completar calendario recurrente, notificaciones y reportes por periodo.
6. Preparar despliegue con HTTPS, recuperación de cuentas, respaldo y validación con usuarios.

## Limitaciones conocidas

- Las operaciones de consulta cargan los registros del módulo y filtran en Python; se necesita paginación y filtrado SQL para grandes padrones.
- No hay bloqueo optimista: dos ediciones simultáneas pueden sobrescribirse.
- Las inscripciones no tienen todavía control transaccional suficiente para cupos con alta concurrencia.
- Un secretario puede editar el estado de sus documentos y solicitudes; aún no existe una revisión institucional separada.
- Quien tiene permiso de gestión puede eliminar registros. El historial conserva la acción, pero no recupera el contenido eliminado.
- Reemplazar un adjunto no conserva su versión anterior; pueden quedar archivos huérfanos para limpieza administrativa futura.
- El límite de intentos de acceso es por correo y no sustituye un control de abuso de infraestructura.
- Un cambio de contraseña no invalida otras sesiones existentes; la desactivación de cuenta sí bloquea sus solicitudes posteriores.
- El navegador remoto no pudo conectarse al servidor local durante esta entrega: las pruebas realizadas son de servidor y no validan la apariencia en dispositivos reales.

No cargar padrones reales ni utilizar saldos del prototipo como contabilidad oficial hasta completar la revisión y preparación del piloto.

## Actualización de diseño v0.2

Se incorpora portada editorial, imágenes generadas identificadas como referencia, menú público adaptable, accesos rápidos, tarjetas de eventos, filtros SEC/GJ, información por grupo, galería de ejemplo y preguntas frecuentes. Los cambios se describen en `ACTUALIZAR_v0.2.md`; las ampliaciones funcionales pendientes de la tabla anterior mantienen su estado.

## Actualización v0.3 — reemplaza los estados anteriores de estas funciones

Se implementan identidad basada en el logo DEPEC y fotografía de Jerusalén, configuración del local y color por iglesia, hero con archivos propios clasificados, versículo diario local, collage de eventos por orientación, estado Finalizado automático al consultar, enlaces Maps y tarjeta lateral del calendario. También se añaden registro y aprobación de miembros, mensajes moderados, álbumes con contribuciones por alcance y metadatos de autor/iglesia/álbum, y perfiles públicos autorizados de directiva. La migración es aditiva y conserva el contenido anterior. Detalles y límites en `ACTUALIZAR_v0.3.md`.

## Actualización v0.4

Se añaden diseño retro y temas claro/oscuro/sistema; comunidades solo en DEPEC y antes de eventos; collage limitado a seis tarjetas, cuadrado en escritorio; escenario ficticio completo de DEPEC/Jorge Chávez con afiches, líderes, miembros y álbumes; personalización del hero y lista de versículos por iglesia; aniversario configurable con cálculo de años; perfiles públicos optativos de miembros con avatares y revisión por líderes. Se incluyen vistas estáticas del diseño. Información aportada, ejemplos y límites se detallan en `ACTUALIZAR_v0.4.md`.

## Actualización v0.4.1

Tablón público de anuncios por organización, con prioridad, inicio, vencimiento y cuenta regresiva. Los borradores, anuncios retirados, programados o vencidos no se muestran. La sección completa se omite si está vacía. Los anuncios vencidos se conservan en el panel; JavaScript retira los visibles al vencer sin recargar. Gestión por los permisos existentes. Detalles en `ACTUALIZAR_v0.4.1.md`.

## Actualización v0.4.4

DEPEC sin local propio; mapas de las iglesias autorizados por CSP, resolución de enlaces cortos de Google Maps y conservación de su enlace original; insignias SVG centradas por cargo; tarjetas de miembros y testimonios compactas; calendario de cumpleaños separado con filtro por iglesia, navegación mensual, consentimiento público sin año ni edad y calendario privado sujeto a los permisos del padrón. Detalles en `ACTUALIZAR_v0.4.4.md`.

## Actualización v0.4.5

Collage de eventos en cuatro columnas con colocación calculada y rellenos decorativos sin enlaces ni fechas, adaptación a dos/una columnas y borde dorado para DEPEC en la portada general. DIRECTIVA DEPEC solo en esa portada; directorio de miembros reservado a las páginas de iglesias; mural de mensajes aprobados con autor y color de iglesia.

## Actualización v0.4.6

Visor accesible para imágenes públicas, ajuste a pantalla/tamaño original, navegación por grupo de imágenes y controles de teclado. Burbuja de contacto por organización con edición autorizada, opción de ocultar, enlaces seguros a WhatsApp/llamada/correo y configuración independiente de DEPEC, iglesias y sus álbumes. No se cambian permisos de acceso a imágenes ni se envían mensajes automáticamente.
