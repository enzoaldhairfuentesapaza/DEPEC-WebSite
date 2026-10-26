# DEPEC v0.3 — Identidad y comunidad

## Antes de actualizar

Detén el servidor. Conserva tu carpeta `.git`, tu entorno `.venv`, tus copias y **toda la carpeta `instance`**. Ejecuta el `backup.py` de tu versión actual antes de copiar los archivos nuevos. El ZIP no contiene bases, claves ni archivos privados de ejecución.

1. Copia los archivos de `depec` sobre tu proyecto.
2. Ejecuta `iniciar.bat`: el marcador de dependencias de esta versión es nuevo, por lo que instalará también Pillow y tzdata.
3. Abre http://127.0.0.1:5000 y recarga con Ctrl+F5.

Alternativa manual en Windows:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app run upgrade-db
.\.venv\Scripts\python.exe run.py
```

El esquema se actualiza al iniciar sobre una base existente. La migración añade campos y tablas; no elimina usuarios ni registros. Es idempotente. Los adjuntos de eventos/publicaciones anteriores se incorporan al catálogo de archivos. Las fotografías de la antigua Galería se conservan en álbumes «Galería anterior · [grupo]». La antigua pantalla Galería permanece por compatibilidad; para nuevos álbumes utiliza **Archivos y álbumes**.

## Recorrido para configurar la página

### 1. Identidad y local

En el panel, abre **Identidad y local**. Presidencia, vicepresidencia, secretaría y el cargo genérico Líder pueden configurar las iglesias de su alcance; DEPEC puede configurar todas.

- Color principal de la página de la iglesia.
- Fotografía del grupo.
- Mensaje y nombre de la iglesia.
- Dirección exacta de su local y, opcionalmente, enlace HTTPS de Google Maps.
- Horario habitual.

La foto enviada de SEC Jerusalén se muestra como imagen inicial de ese grupo. Las otras iglesias muestran un diseño explícitamente marcado «Fotografía por agregar», sin atribuirles fotografías ajenas. El logo enviado de DEPEC está integrado sin alterar la imagen original.

### 2. Hero: archivos de la organización

Abre **Archivos y álbumes** y selecciona «Publicar en nombre de DEPEC». Elige **Afiche** o **Fotografía**, título y visibilidad pública. Los ocho archivos públicos más recientes de DEPEC se muestran en su hero, con navegación anterior/siguiente. Una SEC/GJ muestra únicamente sus propios archivos en su hero.

- El afiche se muestra completo, sin cortar información.
- La fotografía utiliza una presentación fotográfica.
- Se indica quién lo subió, la iglesia en cuyo nombre se publicó, el álbum y su identificador.
- Sin archivos publicados, el hero muestra la identidad DEPEC o la imagen de la iglesia; no inventa publicaciones.
- Los afiches adjuntos a eventos y publicaciones también se incorporan al catálogo, respetando visibilidad y borradores.

### 3. Eventos y calendario

El local se completa con la dirección configurada de la iglesia. Puedes cambiar el lugar y añadir otra dirección para un evento particular. El enlace «Cómo llegar» abre Google Maps; si no existe una dirección confirmada, no se inventa una ubicación.

El servidor usa **America/Lima**. Los estados visibles son Pronto, En curso, Reprogramado, Finalizado y Cancelado. Al consultar el sitio después de la hora de cierre, el sistema persiste Finalizado y registra la transición. No requiere que un líder lo cambie manualmente; no es un proceso programado que se ejecute mientras el servidor está apagado. Las cancelaciones se conservan.

El collage adapta cada tarjeta a la orientación real de su imagen: horizontal o vertical. Se conserva el afiche completo. La iglesia tiene una etiqueta prominente con su color; fecha, hora, estado y ubicación quedan visibles.

En el calendario, seleccionar un evento muestra su tarjeta a la derecha; en pantallas pequeñas aparece debajo. El enlace incluye el evento seleccionado, por lo que también funciona sin JavaScript y se puede compartir. Solo se muestran datos autorizados para esa vista pública o privada.

### 4. Álbumes y contribuciones

Crea un álbum en **Archivos y álbumes**, por ejemplo «Campamento de líderes» o «Agradecidos al Rey 2026». En instalaciones nuevas de demostración ya existen esos dos álbumes vacíos; no se añaden automáticamente a bases existentes.

- Los líderes de cualquier iglesia pueden aportar fotografías a los álbumes públicos de DEPEC, publicando en nombre de su propia iglesia.
- En álbumes de una SEC/GJ, solo sus líderes y DEPEC pueden aportar.
- La creación de álbumes requiere permiso de gestión de Galería; presidencia, secretaría y Líder lo tienen de forma predeterminada. Otros líderes pueden recibirlo mediante permisos adicionales.
- Cada foto conserva autor de carga, iglesia, álbum, fecha e ID.
- Puedes cargar hasta 20 imágenes por solicitud, con un límite total de 10 MB y 40 megapíxeles por imagen.
- Los archivos y álbumes internos no se publican en la portada.

### 5. Registro de miembros y mensajes

La página pública incluye **Solicitar registro como miembro**. La persona elige su SEC/GJ y crea una contraseña. Su cuenta queda desactivada y pendiente de aprobación.

En **Solicitudes y mensajes**, presidencia, vicepresidencia, secretaría o el cargo Líder de su iglesia revisa la solicitud. Los líderes de otra iglesia no pueden aprobarla. DEPEC puede supervisar todas.

Al aprobar, la cuenta puede iniciar sesión e ir a **Mi comunidad**, pero no recibe cargos ni acceso a padrón, tesorería o documentos. Los mensajes enviados quedan pendientes de otra revisión. Solo se publican mensajes aprobados de miembros con pertenencia aprobada y cuenta activa. Se muestran en su iglesia y en la página general DEPEC. Rechazar o retirar la aprobación de un mensaje lo oculta.

La comprobación de pertenencia la realiza la directiva: todavía no hay verificación automática de correo, envío de avisos ni recuperación de contraseñas por email. La persona puede consultar a sus líderes para saber si fue aprobada.

### 6. Directiva pública

Los cargos se asignan en **Grupos y directivas**. Se incluyen Asesor y Líder, además de los cargos anteriores; se admiten varios vocales y cargos opcionales.

En **Directiva pública**, cada líder puede completar su perfil; los responsables de la iglesia pueden gestionar los de su alcance. Fotografía, mensaje y teléfono se publican solo cuando se marca la autorización correspondiente.

La página muestra únicamente cargos activos y perfiles autorizados. Los principales se ordenan por cargo; presidencia recibe un tratamiento visual dorado. Los líderes adicionales aparecen después y pueden destacarse. No se inventan personas ni teléfonos para rellenar cargos vacíos. Un líder sin fotografía publicada muestra «Foto por agregar».

### 7. Versículo diario

Se utiliza una lista local de 15 textos breves de **Reina-Valera 1909**, de dominio público. El orden se mezcla de forma determinista y cambia cada día según la fecha de Perú; todos ven el mismo versículo durante ese día. El ciclo evita repeticiones consecutivas y vuelve a empezar al completar la lista. No usa una API ni requiere Internet. Se puede ampliar en `app/community_data.py`.

## Diseño y menú

Nueva paleta inspirada en el logo: rojo, borgoña, blanco y detalles dorados. El color definido por cada iglesia adapta acentos y matices, conservando la estructura común. Las páginas SEC/GJ tienen un enlace visible para volver a DEPEC.

El menú móvil usa `details/summary` nativo y funciona sin JavaScript. También cierra con Escape o al elegir una sección cuando JavaScript está disponible. Se añaden tarjetas por iglesia con fotografía y texto al frente, en lugar de iniciales grandes.

## Pruebas y límites de esta entrega

Se ampliaron las pruebas funcionales para archivos, separación DEPEC/iglesias, permisos de álbumes, aprobación de miembros, moderación de mensajes, orientación, local por defecto, Maps, versículo diario, directivas y migración. También se verifica la sintaxis de JavaScript. Esto no sustituye la revisión visual en navegadores y dispositivos reales: la infraestructura del navegador remoto no comparte el servidor local.

Sigue siendo un prototipo: no incluye envío de correo, antivirus de archivos, paginación de grandes álbumes, eliminación/restauración de álbumes desde interfaz, proceso de auditoría institucional ni controles de concurrencia suficientes para un uso masivo. Los teléfonos y fotografías de personas reales deben publicarse con su autorización desde el formulario.

## Guardar esta versión en GitHub

Después de copiar y probar en tu repositorio local:

```powershell
git status
git add app tests requirements.txt iniciar.bat README.md ACTUALIZAR_v0.3.md docs
git commit -m "Identidad DEPEC, comunidad verificada, álbumes y calendario detallado"
git push origin main
```

Si aún no existe la etiqueta:

```powershell
git tag -a v0.3.0 -m "DEPEC: identidad y comunidad"
git push origin v0.3.0
```
