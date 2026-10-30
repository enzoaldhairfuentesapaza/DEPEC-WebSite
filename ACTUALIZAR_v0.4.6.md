# v0.4.6 — imágenes ampliables y contacto

## Actualización

Detén el servidor y copia esta entrega sobre el proyecto. Conserva `instance`, `.venv`, `.git` y tus respaldos. Ejecuta `iniciar.bat` y recarga con Ctrl+F5. Se añade automáticamente la configuración de contacto a las organizaciones existentes, sin borrar sus datos. No hay nuevas dependencias para ejecutar la aplicación.

## Ver imágenes en grande

Haz clic en una fotografía o afiche del contenido público: hero, eventos, álbumes, tarjetas de iglesias, líderes o miembros. El visor muestra la imagen completa y permite:

- Ajustar a pantalla o ver su tamaño original con desplazamiento.
- Pasar a la anterior/siguiente del mismo grupo de imágenes, con botones o flechas del teclado.
- Abrir el archivo original en otra pestaña.
- Cerrar con el botón, Escape o clic fuera del visor.

Hay botones de ampliación para acceso con teclado. Al cerrar, el foco regresa al control que abrió la imagen. Las tarjetas conservan sus enlaces de texto para visitar la iglesia o el álbum. En el hero se añade un enlace a Ver álbum cuando corresponde. Sin JavaScript, los enlaces originales siguen disponibles.

Se omiten el logo de navegación, los rellenos decorativos del collage y los avatares del formulario de selección. Las imágenes añadidas al cambiar el detalle del calendario también reciben el visor. No se modifican los permisos de los archivos: una imagen privada sigue requiriendo autorización.

## Burbuja Contáctanos

Cada organización dispone de su burbuja, con el color y nombre de su página. Se conserva ese alcance en los álbumes y calendarios filtrados por iglesia. DEPEC tiene su configuración independiente y no necesita un local físico para tener contacto.

En **Panel → Contacto público** selecciona la organización y configura:

- Mostrar u ocultar la burbuja.
- Texto del botón, título y mensaje de bienvenida.
- Nombre del responsable o equipo, y horario de atención.
- Número de WhatsApp con código de país, teléfono y correo público.
- Texto inicial de la conversación de WhatsApp.

Los medios son opcionales. Si no hay ninguno, la burbuja informa que la directiva aún no ha publicado sus datos. No se inventan números o direcciones de correo para la demo. El visitante decide si abre WhatsApp, realiza una llamada o escribe un correo; no se envía ningún mensaje automáticamente.

Gestionan el contacto quienes tienen permiso para editar la identidad de su iglesia: presidencia, vicepresidencia, secretaría, prosecretaría y cargo Líder, además del administrador y los cargos DEPEC con alcance correspondiente. Un miembro aprobado no obtiene permiso para cambiar el contacto. Los cambios se registran en el historial y no afectan la configuración de otras iglesias.

La burbuja funciona como un panel desplegable, también sin JavaScript. Con JavaScript se cierra al pulsar Escape o hacer clic fuera. Los datos configurados son públicos: utiliza solo medios autorizados para ese fin.

## Verificación

70 pruebas del servidor, incluyendo migración sin pérdida de datos, validación de teléfonos/correo, alcance por organización y álbum, ocultación de la burbuja, permisos, CSRF y escape de texto. JavaScript comprobado sintácticamente.

También se ejecutó una comprobación en un DOM simulado: apertura del visor, navegación, tamaño original, cierre, retorno del foco, enlaces sin botones anidados, filtros de iglesias, Escape de contacto e imágenes añadidas dinámicamente al calendario. Esto no sustituye la revisión visual de tamaños y distribución en un navegador real.
