# DEPEC · Comunidades, Secretaría y Tesorería

Versión **7.0.0**, etiqueta prevista **v7.0.0**. Sistema web en español para DEPEC y sus SEC/GJ de Arequipa Sureste, construido con Flask, Jinja, SQLite y JavaScript. Se ejecuta localmente en un solo servidor.

DEPEC reúne a las iglesias: no tiene local ni padrón propio. Sus integrantes son la suma de las iglesias; su directiva, archivo y caja sí pertenecen a DEPEC.

## Funciones del sistema

- Páginas DEPEC y por iglesia, colores personalizables, estilo juvenil, temas claro/oscuro, hero configurable y versículos diarios.
- Comunidades, directivas por cargo, perfiles públicos moderados, contacto y preguntas frecuentes.
- Calendario de eventos y cultos semanales con temáticas y cancelaciones por fecha; calendario de cumpleaños separado.
- Eventos con destinatarios, invitaciones privadas, collage, imágenes opcionales, orientación ajustable y vista previa en la misma pantalla.
- Anuncios con vencimiento, álbumes con buscador y visor de imágenes.
- Padrón por iglesia vinculado a cuentas, foto opcional y avatares, descripción personal, cumpleaños, bautismo y actividad mediante switches privados.
- Registro público de miembros sujeto a aprobación, registro por líderes y edición personal sin acceso al padrón de otros integrantes.
- Vista general por cargo, resumen de integrantes e iglesias, caja propia y próximos eventos por organización.
- Secretaría organizada por reunión: convocatorias ordinarias/extraordinarias, actas con asistentes, resumen, acuerdos, correspondencia, folio y archivo digital versionado.
- Actas descargables en DOCX y modelos editables de acta, credencial, carta y plan anual.
- Plan anual por organización y año; DEPEC abre/cierra recepción con fecha límite, recibe copias, observa y registra su recepción.
- Credenciales de las iglesias convocadas: envío, copia conservada, revisiones y recepción por DEPEC. En estas reuniones se registra una sola acta, propiedad de DEPEC.
- Correspondencia recibida y enviada, documentos, buscador y vinculación con la reunión donde se revisó.
- Biblioteca común de plantillas publicadas por DEPEC, accesible a las directivas.
- Tesorería por organización: ingresos/egresos, descripción, monto, fecha, efectivo/banco, comprobantes y movimientos pendientes/aprobados.
- Proyectos ligados opcionalmente a eventos y categorías configurables, como música, logística o decoración.
- Deudas por cobrar/pagar, pagos parciales, saldos y movimientos de caja vinculados; protección contra duplicados y sobrepagos.
- Reportes por año, mes, rango de fechas, proyecto y categoría; saldo previo/al cierre y desgloses mensuales y por agrupación.
- Excel real `.xlsx` con resumen, movimientos, meses, categorías, proyectos y deudas, preparado para imprimir.
- Historial de acciones, archivos privados, CSRF, contraseñas con hash y copias de seguridad.
- Cuenta global de pruebas para cambiar de rol e iglesia sin cerrar sesión.

## Inicio en Windows

1. Instala Python 3.11+ con el lanzador `py`.
2. Extrae el proyecto y abre la carpeta `DEPEC_WebSite`.
3. Ejecuta `iniciar.bat` y abre **http://127.0.0.1:5000**.

El script instala dependencias en `.venv`, inicializa una base demo solo si no existe y conserva los datos anteriores. En esta entrega actualiza las dependencias para Excel y DOCX. La primera instalación requiere Internet.

Alternativa en PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app run init-db
.\.venv\Scripts\python.exe -m flask --app run seed-demo
.\.venv\Scripts\python.exe run.py
```

En Linux/macOS/WSL sustituye el ejecutable por `.venv/bin/python` después de crear el entorno con `python3 -m venv .venv`.

## Actualizar una instalación existente

Detén el servidor y haz una copia con `backup.py`. Copia el código conservando `instance/`, `.venv/` y `.git/`. Ejecuta `iniciar.bat` o instala `requirements.txt` con el Python del entorno y reinicia. Recarga con Ctrl+F5.

Las nuevas tablas se crean de forma aditiva, sin reiniciar SQLite. Los movimientos de caja existentes se usan directamente en los reportes. Los documentos, entregas, actividades y reuniones antiguos siguen en **Secretaría → Archivo de versiones anteriores**. No se inventan asociaciones entre actas y reuniones que antes no existían.

## Recorrido de Secretaría

1. Como directiva DEPEC, abre **Secretaría → Recepción de planes**, elige año, plazo e indicaciones y habilita la recepción.
2. Cada iglesia guarda su plan en **Mi plan anual**, incluso si la recepción está cerrada. Cuando esté abierta, pulsa **Enviar última versión a DEPEC**.
3. DEPEC registra **Recibido** u **Observado**, con su nota. La copia enviada queda fija: una revisión local posterior no la reemplaza hasta enviarla nuevamente.
4. Desde **Reuniones y actas**, crea una reunión ordinaria o extraordinaria. DEPEC elige si convoca solo a su directiva o a iglesias determinadas. Las iglesias crean reuniones internas propias.
5. Las iglesias convocadas encuentran la reunión en el resumen de Secretaría, suben su credencial e indican sus delegados. DEPEC la recepciona; ambos consultan el mismo documento conservado.
6. La Secretaría de la organización convocante llena el acta, conserva su copia digitalizada y descarga el DOCX si lo necesita. **Registrada/Firmada** son etiquetas del archivo, no firmas digitales.
7. Registra cartas recibidas/enviadas en **Correspondencia** y asócialas a una reunión para encontrarlas junto a su acta.
8. Descarga modelos iniciales o publica los formatos de DEPEC en **Plantillas**. Los modelos incluidos son referencias editables, no documentos oficiales ya completados.

## Recorrido de Tesorería

1. En **Proyectos y categorías**, crea el campamento o actividad y sus categorías. No es obligatorio que exista un evento público.
2. Registra un ingreso o egreso con su descripción e importe. Para incorporar dinero ya existente, registra un ingreso de categoría **Saldo inicial**.
3. Filtra **Caja y reportes** por año/mes o por rango, proyecto y categoría. Solo los movimientos aprobados integran los totales.
4. El **resultado del filtro** corresponde a esa selección. El **saldo de caja** corresponde a toda la organización hasta la fecha de cierre, aunque filtres por proyecto/categoría.
5. En **Deudas**, registra lo que deben a la organización o lo que esta debe. Esto no cambia el efectivo. Cada pago/cobro parcial genera un único egreso/ingreso y reduce la deuda.
6. Si también debes reflejar el dinero de un préstamo recibido o entregado originalmente, registra ese movimiento inicial por separado; crear la deuda no lo duplica.
7. Anula un movimiento incorrecto para retirar su efecto y conservar el historial. Anular un pago restaura su saldo pendiente. Los pagos no se editan directamente.
8. Descarga Excel para imprimir o continuar trabajando. Las deudas se calculan al cierre del periodo y se filtran por proyecto; la categoría pertenece a los movimientos.

## Permisos y separación de archivos

- Presidencia, Vicepresidencia y cargo genérico Líder gestionan Secretaría y Tesorería de su propia organización.
- Secretaría/Prosecretaría gestionan planes, actas, credenciales, correspondencia y plantillas DEPEC si pertenecen a DEPEC.
- Los demás líderes consultan la Secretaría de su organización; los formularios de edición quedan reservados a los cargos anteriores.
- Tesorería/Protesorería gestionan caja y deudas de su organización. Secretaría y Vocales no acceden al detalle de tesorería por su cargo.
- Una asignación DEPEC no concede acceso al archivo interno ni a la caja de otra iglesia. Solo recibe las copias de planes y credenciales que esta entrega.
- La supervisión DEPEC sobre eventos, padrón y páginas conserva el alcance general del sistema. Los miembros no acceden a estas oficinas privadas.
- El administrador técnico global mantiene capacidades de soporte; es distinto del cargo Presidente DEPEC. Para comprobar los permisos reales, selecciona ese cargo en la cuenta de pruebas.
- Los cargos se activan/finalizan desde Organización. El periodo es una etiqueta y no vence automáticamente.

## Cuentas demo

Contraseña: **`DepecDemo2026!`**.

| Correo | Cargo |
|---|---|
| admin@depec.demo | Administrador técnico global |
| presidencia@depec.demo | Presidencia DEPEC |
| israel@depec.demo | Presidencia SEC Israel |
| secretaria@depec.demo | Secretaría SEC Israel |
| tesoreria@depec.demo | Tesorería SEC Israel |
| vocal@depec.demo | Vocal SEC Israel |

Cuenta global de pruebas: **`pruebas@depec.demo` / `DepecPruebas2026!`**. Cambia cargo e iglesia en el selector PRUEBAS. Sus cambios afectan la base de pruebas; las operaciones no se simulan. Más detalles en [CUENTA_DE_PRUEBAS.md](CUENTA_DE_PRUEBAS.md).

## Guardar y etiquetar el hito en Git

Después de copiar el código dentro de tu repositorio existente:

```powershell
git add .
git commit -m "feat: secretaria y tesoreria digital"
.\.venv\Scripts\python.exe etiquetar_version.py
git push
git push origin v7.0.0
```

El script lee `VERSION`, exige un commit sin cambios pendientes y crea una etiqueta anotada `v7.0.0`. No sobrescribe una etiqueta existente en otro commit. Puedes usar `etiquetar_version.py --push` para publicar también la etiqueta en `origin`. El ZIP no contiene tu carpeta `.git`: copiar archivos no crea por sí solo un commit ni una etiqueta.

Las notas de entregas anteriores están en `docs_locales/`, ignorado por Git. Este README reúne las funciones actuales, sin añadir una sección por cada entrega. El historial real está en `git log --oneline`.

## Pruebas y copia de seguridad

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Las pruebas usan bases temporales y cubren permisos, CSRF, separación de organizaciones, recepción de copias, documentos inválidos, cuentas, pagos, duplicados, importes y Excel. No sustituyen las pruebas visuales con las directivas en sus equipos.

Con el servidor detenido, ejecuta `python backup.py` usando el Python del entorno. Guarda el ZIP privado de `backups/`. Para restaurarlo, detén el servidor y recupera su contenido en `instance/` de una instalación compatible.

## Instalación sin datos de demostración

Ejecuta `init-db` y `create-admin`, sin ejecutar `seed-demo`. Crea las SEC/GJ, cuentas y cargos desde Organización. La instalación incluye únicamente DEPEC antes de configurarla.

## Arquitectura y estado

`app/secretariat.py` implementa la oficina documental; `app/treasury.py` y `treasury_export.py`, caja y Excel. `office_common.py` centraliza permisos y documentos, y `office_schema.sql` incorpora las tablas nuevas. Los adjuntos se guardan fuera de `static/`, con versiones conservadas y descargas autorizadas. Los importes se calculan con Decimal/céntimos, sin sumar floats en el servidor.

El proyecto sigue siendo una base de prototipo: faltan validación institucional, despliegue, recuperación de cuentas, conciliación bancaria y cierres contables inmutables. El archivo de actas no reemplaza por sí solo firmas físicas ni incorpora firma digital. Más detalles en [docs/ALCANCE.md](docs/ALCANCE.md) y [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md).
