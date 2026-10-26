# DEPEC v0.4 — Un giro retro

## Mirar primero el diseño

Descomprime el proyecto y abre en tu navegador:

- `preview/index.html`: portada de DEPEC.
- `preview/jorge-chavez.html`: ejemplo de la página de Jorge Chávez.

Estas vistas estáticas usan las mismas plantillas, estilos e imágenes de la aplicación. Permiten probar los temas, el menú, filtros y detalles locales. Los enlaces al calendario, álbumes, registro y formularios requieren iniciar el servidor. Las fechas y los ejemplos de esas vistas son una fotografía del momento en que se generaron; no representan eventos oficiales.

Para regenerarlas sin modificar tu base:

```powershell
.\.venv\Scripts\python.exe generar_vista_previa.py
```

## Actualizar la aplicación

1. Detén el servidor y respalda la carpeta `instance` con el script de respaldo de tu instalación actual.
2. Copia los archivos nuevos sobre tu proyecto, conservando `.git`, `.venv`, `instance` y tus respaldos.
3. Ejecuta `iniciar.bat`. El esquema se amplía al iniciar; no es necesario borrar ni volver a cargar la base.
4. Abre http://127.0.0.1:5000 y recarga con Ctrl+F5.

En bases que conservan la cuenta **admin@depec.demo**, se añaden una sola vez los ejemplos v0.4. El marcador `retro-demo-v04` evita duplicarlos. Son ejemplos adicionales, no sustituyen los usuarios ni registros previos. La configuración de prueba de Jorge Chávez se aplica si su título del hero aún estaba vacío. Se refuerzan las paletas de los grupos de demostración.

Una base real, sin esa cuenta demo, recibe la migración pero **no** personas, eventos ni datos ficticios. Sus líderes configuran sus páginas desde Identidad y local. El código fuente no contiene bases de ejecución ni claves.

## Qué cambia en la portada

- Paleta intensa de cada organización: rojo en DEPEC; azul y amarillo como propuesta de prueba en Jorge Chávez.
- Diseño retro con tipografía serif, papel, stickers, marcos y sombras de tinta.
- Selector de tema: **Sistema → Claro → Oscuro → Sistema**. Se guarda en el navegador. En celular está dentro del menú.
- «Encuentra tu comunidad» aparece únicamente en DEPEC, antes de los eventos. Las SEC/GJ mantienen el enlace para regresar a la página principal.
- Los próximos eventos muestran un máximo de **seis tarjetas**, seleccionadas por fecha. En escritorio se colocan en un mosaico cuadrado con espacios verticales y horizontales. El tamaño de los afiches se conserva dentro de sus marcos; la tarjeta completa del calendario permite ver su información con más espacio.
- En celular el mosaico cambia de proporción para mantener textos y controles legibles. En pantallas muy estrechas se utiliza una columna.

## Jorge Chávez: datos aportados y datos de ejemplo

Se incluyen la fotografía recibida y estos textos:

**Título:** Más que una iglesia, una familia que camina junta

**Descripción:** Nos conocemos bien, compartimos la vida sin filtros y nos une el gozo de adorar juntos. Aquí siempre hay un lugar para ti.

**Colosenses 3:14:** Sobre todo, vístanse de amor, que es el vínculo perfecto que nos une a todos.

El texto del versículo se identifica como aportado por la comunidad; no se le atribuye una traducción bíblica que no fue especificada.

**Enlace de ubicación aportado:** https://maps.app.goo.gl/KSo2PasAcs3HdyU36

El enlace se guarda directamente. No se obtuvo una dirección postal verificable del enlace corto, por lo que el lugar se indica como «Local de la Iglesia Jorge Chávez · ver ubicación exacta en Google Maps». Los eventos usan ese local y abren el enlace proporcionado. Para DEPEC se usa una dirección expresamente marcada como ejemplo para mostrar el formulario.

El aniversario de Jorge Chávez se mantiene **por confirmar**, porque no se proporcionó la fecha real. DEPEC tiene una fecha ficticia de aniversario para demostrar el cálculo, visible como dato de demostración. No debe confundirse con la fundación histórica.

## Ejemplos para explorar

En bases demo se agregan:

- Seis líderes ficticios de DEPEC y seis de Jorge Chávez, con dos retratos generados con IA reutilizados como referencia visual.
- Doce miembros ficticios con perfiles, versículos, gustos y dones. Ocho pertenecen a Jorge Chávez y cuatro a Israel.
- Seis eventos ficticios de DEPEC y seis de Jorge Chávez, con afiches retro horizontales y verticales, fechas futuras relativas al día de carga y un caso reprogramado.
- Tres álbumes de prueba por organización, con fotografías generadas y marcadas como escenas de ejemplo.
- Mensajes aprobados de demostración.

La foto real de Jorge Chávez no se utiliza para identificar ni asignar nombres a las personas fotografiadas. Los líderes y perfiles de prueba son inventados.

Todas las cuentas de demostración usan **DepecDemo2026!**. Para probar la personalización de un miembro:

- Correo: `miembro-0@demo.depec.local`.
- Contraseña: `DepecDemo2026!`.
- Después de entrar, selecciona «Personalizar mi perfil público».

Para probar un líder ficticio de Jorge Chávez:

- Correo: `lider-3-0@demo.depec.local` en la base inicial, donde Jorge Chávez tiene id 3.
- Contraseña: `DepecDemo2026!`.

También se conservan las cuentas anteriores, incluido `admin@depec.demo`. Los identificadores pueden variar si una instalación fue reorganizada manualmente; consulta Grupos y directivas.

## Hero y versículos personalizables

En **Identidad y local** puedes editar:

- Título y descripción del hero.
- Mensaje de la tarjeta de comunidad.
- Fotografía, color y local.
- Modo del versículo: lista general diaria, lista propia o no mostrar.
- Lista propia, con una línea por texto: `Referencia | Texto`.

Con un versículo se mantiene fijo; con varios rota diariamente, usando la fecha de Perú. No depende de una API. Así cada iglesia elige sus textos sin alterar el contenido de las demás.

## Aniversario y años

Cada portada de organización tiene una sección de aniversario. Configura su fecha de fundación en **Identidad y local**. El sistema calcula los años cumplidos y los que cumplirá en la siguiente celebración. Si falta la fecha, muestra «Por confirmar». Las fechas del 29 de febrero se celebran el 28 en años no bisiestos.

El campo de nota permite marcar fechas de ejemplo o pendientes de verificación.

## Perfiles de miembros

Cada miembro con registro aprobado puede usar **Mi comunidad → Personalizar mi perfil público** para:

- Elegir un avatar: Luz, Paloma, Biblia, Pez o Cruz.
- Subir una fotografía propia, o volver a un avatar.
- Escribir un mensaje y versículo.
- Compartir gustos, dones y cosas que no le gustan.
- Autorizar o retirar su publicación.

Los campos son opcionales. No se publica automáticamente el padrón privado, fechas de nacimiento, bautismo, teléfonos ni correos. El directorio público contiene los perfiles que sus miembros han autorizado y sus líderes han aprobado. DEPEC los reúne; cada SEC/GJ muestra solo los de su organización.

Cada edición vuelve a **Pendiente**, incluso si el perfil había sido aprobado, y deja de publicarse hasta la nueva revisión. Los líderes revisan el texto, imagen y demás campos en **Solicitudes y mensajes → Perfiles públicos de miembros**. Ningún miembro puede editar el perfil de otro ni aprobar su propia publicación. Los responsables de otra iglesia no pueden aprobarlo; DEPEC conserva su alcance general.

## Verificación y límites

Se verifican servidor, permisos, migración, límite y orden de secciones, configuración de versículos, cálculo de aniversarios, personalización y revisión de perfiles, recursos de las vistas previas y sintaxis de JavaScript. La apariencia y las interacciones finales deben revisarse en un navegador real; las vistas estáticas se incluyen para facilitar esa revisión.

Siguen pendientes las funciones de producción descritas en versiones anteriores: recuperación y avisos por correo, gestión completa de eliminación de datos de demostración, paginación de directorios grandes, controles operativos y auditoría completa. El selector de tema usa JavaScript; el menú móvil conserva funcionamiento nativo sin él.

## Guardar en GitHub

Después de probar en tu copia del repositorio:

```powershell
git status
git add app tests preview generar_vista_previa.py README.md ACTUALIZAR_v0.4.md docs
git commit -m "Diseño retro, temas claro y oscuro, ejemplo Jorge Chávez y perfiles de miembros"
git push origin main
```

Opcional, si aún no existe esa etiqueta:

```powershell
git tag -a v0.4.0 -m "DEPEC retro y comunidad personalizable"
git push origin v0.4.0
```
