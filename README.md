# DEPEC — Comunidad y gestión

Prototipo funcional v0.4.3 para la DEPEC y sus SEC/GJ. Construido con **Flask, Jinja, SQLite y JavaScript**, sin Node ni un frontend separado. Funciona localmente; no está desplegado en Internet. La interfaz y los datos iniciales están en español.

## Novedades v0.4.3 — tarjetas con formato y vista previa

El collage respeta la orientación de cada evento y ocupa menos ancho. El formulario permite formato automático, vertical u horizontal; imagen propia, solo información o tres imágenes genéricas; y vista previa en vivo. Directiva compacta con pines por cargo, tipografía más equilibrada y mapa del local configurable por iglesia. Consulta `ACTUALIZAR_v0.4.3.md`.

## Corrección v0.4.2 — inicio en Windows

Lectura explícita en UTF-8 y reparación automática de la restricción de fotografías creada con codificación incorrecta. Conserva los datos y genera antes una copia de seguridad de la base afectada. Consulta `ACTUALIZAR_v0.4.2.md`.

## Novedades v0.4.1 — tablón de anuncios temporales

En **Panel → Tablón de anuncios** cada organización puede crear avisos con prioridad, fecha de inicio y vencimiento. Solo aparecen en su propia portada durante su vigencia, con una cuenta regresiva. Si no hay anuncios vigentes, no se muestra la sección. Al vencer se retiran de la página, pero se conservan en el panel.

No se cargan anuncios de cancelación como datos demo: el tablón inicia vacío. Instrucciones en `ACTUALIZAR_v0.4.1.md`.

## Novedades v0.4 — retro, claro y oscuro

Diseño retro con colores protagonistas por iglesia, bordes de impresión y modos claro/oscuro/sistema. DEPEC muestra las comunidades antes de los eventos; las páginas SEC/GJ muestran solo su propia comunidad. El collage presenta hasta seis eventos en un marco cuadrado de escritorio y adapta su composición en celular.

Jorge Chávez incluye la foto y los textos aportados por el usuario, su enlace real de Maps, líderes y miembros ficticios, eventos con afiches retro y álbumes con escenas IA. En bases de demostración se cargan los ejemplos una sola vez, sin eliminar registros anteriores. Las instalaciones reales sin la cuenta admin@depec.demo no reciben datos ficticios.

Cada iglesia puede configurar su título, descripción, versículos y fecha de fundación. Los miembros pueden elegir entre cinco avatares cristianos o una fotografía y personalizar su perfil público, sujeto a aprobación.

**Para mirar el diseño sin iniciar el servidor:** después de descomprimir, abre `preview/index.html` o `preview/jorge-chavez.html`. Son vistas estáticas: las acciones de calendario, álbumes y formularios necesitan la aplicación funcionando.

Instrucciones completas en `ACTUALIZAR_v0.4.md`.

## Novedades v0.3

Diseño rojo/borgoña inspirado en el logo DEPEC, fotografía real de SEC Jerusalén, hero con los últimos archivos de la organización, distinción afiche/fotografía, versículo diario local, collage de eventos y calendario con tarjeta lateral. Páginas por iglesia con su color, dirección y Google Maps; registro de miembros sujeto a aprobación y mensajes moderados; álbumes con contribuciones de líderes y perfiles públicos de la directiva.

La migración es aditiva y se ejecuta al abrir una base existente. Antes de actualizar, realiza una copia. Las nuevas dependencias se instalan desde requirements. Lee `ACTUALIZAR_v0.3.md` para los pasos, permisos y limitaciones.

## Novedades visuales de la versión 0.2

Portada rediseñada con navegación pública, accesos rápidos, imágenes de referencia generadas con IA, tarjetas de eventos con detalles, filtros SEC/GJ, información de cada grupo, galería y preguntas frecuentes. Menú móvil con teclado, estados accesibles y navegación usable sin JavaScript. Las fotografías ilustrativas no representan actividades ni integrantes reales.

Si ya tienes la versión anterior, lee `ACTUALIZAR_v0.2.md`. No necesitas reiniciar ni volver a cargar la base de datos.

## Inicio rápido en Windows

1. Instala Python 3.11 o superior, con el lanzador `py` disponible.
2. Descomprime el proyecto y abre la carpeta `depec`.
3. Ejecuta `iniciar.bat`. La primera vez necesita Internet para descargar dependencias.
4. Abre **http://127.0.0.1:5000** en tu navegador.

El script crea un entorno virtual, inicializa SQLite y carga datos ficticios solo cuando no existe una base. No borra datos anteriores.

Alternativa manual en PowerShell, dentro de `depec` (no requiere activar el entorno ni cambiar ExecutionPolicy):

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app run init-db
.\.venv\Scripts\python.exe -m flask --app run seed-demo
.\.venv\Scripts\python.exe run.py
```

## Linux / macOS / WSL

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m flask --app run init-db
.venv/bin/python -m flask --app run seed-demo
.venv/bin/python run.py
```

En Ubuntu puede ser necesario instalar previamente el paquete `python3-venv`.

## Cuentas de demostración

Todas usan la contraseña **`DepecDemo2026!`**. Estos usuarios se crean exclusivamente al ejecutar `seed-demo`, que rechaza bases con usuarios existentes.

| Correo | Acceso de ejemplo |
|---|---|
| admin@depec.demo | Administración completa, cuentas, grupos, cargos y permisos adicionales |
| presidencia@depec.demo | Presidencia DEPEC: información consolidada y gestión de todos los grupos |
| israel@depec.demo | Presidencia de SEC Israel, únicamente ese grupo |
| secretaria@depec.demo | Secretaría de SEC Israel; padrón, documentos, eventos y publicaciones |
| tesoreria@depec.demo | Tesorería de SEC Israel; movimientos financieros y lectura de actividades |
| vocal@depec.demo | Lectura de actividades de SEC Israel; sin padrón, documentos ni tesorería |

Los integrantes, montos y actividades son ficticios. Las descripciones y horarios no son información oficial de las iglesias. Los cumpleaños de ejemplo pertenecen al mes en que cargas la demo.

## Qué puedes probar

- **Página pública:** directorio de los seis grupos, página por grupo, calendario público, noticias, afiches y galería.
- **Panel privado:** resumen de miembros, encuentros, saldo aprobado, tareas y entregas pendientes.
- **Calendario:** vista mensual, navegación entre meses, filtros y colores por organización; eventos de varios días y detalles desplegables.
- **Eventos y publicaciones:** crear, consultar, editar y eliminar; borradores, visibilidad pública/interna, fechas, estado y afiches. Una noticia publicada con fecha futura aparece automáticamente cuando llega su fecha, al consultar la página.
- **Miembros:** padrón privado, bautismo, contacto, apoderado, fechas, estado y observaciones.
- **Cumpleaños:** listado privado mensual. El indicador de compartir se registra, pero no publica cumpleaños en la web.
- **Secretaría:** actas, credenciales, planes, informes, archivos privados y estados documentales.
- **Entregas:** solicitudes documentales por grupo, fecha límite, archivo de respuesta y observaciones.
- **Tesorería:** ingresos/egresos en PEN, efectivo/banco, categorías, comprobantes, relación con evento, aprobación y saldo acumulado de movimientos aprobados.
- **Plan de trabajo:** actividades, objetivos, responsable, presupuesto, periodo y avance.
- **Reuniones y tareas:** agenda, acuerdos escritos, responsables, vencimiento y estados.
- **Asistencia e inscripciones internas:** registro por miembro del grupo anfitrión; cupos controlados al inscribir. No hay registro público de visitantes.
- **Organización:** crear/editar grupos, crear/desactivar usuarios, asignar cargos por periodo y finalizar cargos conservando el historial. Admite varios vocales y varios cargos por persona.
- **Permisos adicionales:** administrador concede lectura o edición de un módulo, por grupo; por ejemplo, permitir publicaciones a un vocal. Son aditivos a los permisos del cargo.
- **Reportes:** cifras acumuladas por organización, CSV para Excel e impresión/guardar PDF desde el navegador.
- **Cuenta:** cambio de contraseña y cierre de sesión.
- **Historial:** creación, cambios, eliminaciones y administración registrados con usuario y fecha.

## Recorrido sugerido

1. Visita el inicio y entra a SEC Israel. Abre el calendario general y filtra por grupo.
2. Ingresa como administrador. Revisa el panel y crea un evento para Israel.
3. Registra una publicación y cambia entre borrador, interna y pública.
4. Revisa el padrón y el listado de cumpleaños.
5. Adjunta un PDF de prueba en Secretaría y descárgalo desde el panel.
6. Registra un ingreso pendiente: no suma al saldo. Cámbialo a aprobado y comprueba el reporte.
7. Abre Asistencia desde un evento e inscribe a un miembro.
8. Cierra sesión e ingresa como tesorería: no podrá acceder al padrón de Israel ni gestionar otros grupos.
9. Como administrador, concede edición de publicaciones a un vocal y prueba esa cuenta.

## Estructura

```text
depec/
  run.py                    Entrada de la aplicación
  iniciar.bat               Arranque de demostración para Windows
  requirements.txt          Dependencias de ejecución
  requirements-dev.txt      Dependencias de pruebas
  backup.py                 Copia consistente de SQLite y archivos
  app/
    __init__.py             Rutas, acceso, validación y operaciones
    modules.py              Definición de formularios por módulo
    schema.sql              Esquema SQLite
    seed.py                 Datos ficticios
    templates/              Páginas Jinja
    static/                 CSS y JavaScript locales
  tests/test_system.py      Pruebas funcionales y de permisos
  docs/                     Arquitectura, alcance y evolución
```

Al ejecutar se genera `instance/`, con SQLite, clave de sesión y archivos. No compartas esa carpeta cuando contenga información real. El ZIP entregado excluye datos de ejecución, claves, entornos virtuales y cachés.

## Permisos predeterminados

| Cargo | Actividades, planes, tareas, galería | Padrón / Secretaría / Entregas | Tesorería |
|---|---|---|---|
| Presidente / Vicepresidente | Leer y gestionar | Leer y gestionar | Leer y gestionar |
| Secretario / Prosecretario | Leer y gestionar | Leer y gestionar | Sin acceso |
| Tesorero / Protesorero | Leer | Sin acceso | Leer y gestionar |
| Vocal | Leer | Sin acceso | Sin acceso |

Un cargo DEPEC se aplica a todas las organizaciones. Un cargo SEC/GJ se limita a su grupo. El administrador gestiona cuentas y permisos. Finalizar un cargo no revoca los permisos adicionales que hayan sido concedidos: estos se revocan por separado desde Organización.

Esta matriz es una propuesta inicial, no un reglamento oficial. Los periodos se conservan como etiquetas; el administrador debe finalizar los cargos, porque no vencen automáticamente por fecha.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

En Linux usa `.venv/bin/python`. Las pruebas crean bases temporales independientes. Cubren páginas, autenticación, CSRF, aislamiento, roles, CRUD, documentos, calendario, cupos, CSV y cambios de cuenta. No equivalen a una auditoría de seguridad ni a validación visual en todos los dispositivos.

## Copias de seguridad

Con la aplicación detenida para mantener también los adjuntos consistentes:

```powershell
.\.venv\Scripts\python.exe backup.py
```

Se genera un ZIP en `backups/`. Para restaurar, detén la aplicación y extrae el contenido en `instance/` de una instalación compatible. Conserva estas copias en un lugar privado. El esquema de esta versión se crea con `init-db`; cambios futuros necesitarán migraciones explícitas.

## Arranque sin datos demo

En una instalación nueva:

```powershell
.\.venv\Scripts\python.exe -m flask --app run init-db
.\.venv\Scripts\python.exe -m flask --app run create-admin
```

No ejecutes `seed-demo` ni el arranque automático de demo en esa instalación. Crea SEC/GJ y usuarios desde Organización. Este modo crea únicamente DEPEC; no carga cuentas ni actividades ficticias. Define `SECRET_KEY` como secreto de entorno si deseas reemplazar la clave local autogenerada.

## Estado y límites

Es una **base ejecutable de prototipo**, no una versión final certificada para datos personales o financieros reales. La matriz completa de funciones implementadas, parciales y pendientes está en `docs/ALCANCE.md`. Falta validar los flujos con las directivas y preparar despliegue, recuperación de cuentas, pruebas visuales y controles operativos.

Se eligió Flask para probar otro framework sin añadir la complejidad de dos servidores. Jinja renderiza las páginas; los formularios usan POST con CSRF y JavaScript mejora navegación, confirmaciones e impresión. No depende de CDN, React, HTMX ni herramientas de compilación.
