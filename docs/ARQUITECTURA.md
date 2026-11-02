# Arquitectura y decisiones

Flask autentica al usuario, valida CSRF en cada POST y renderiza Jinja. JavaScript añade controles y vistas previas, pero no determina permisos. SQLite y los archivos privados están en `instance/`; el ZIP de código no los incluye.

## Dominios

- `records` conserva eventos, integrantes, movimientos de caja y el archivo previo. Los movimientos monetarios se validan con Decimal y se calculan en céntimos enteros. Se conserva el formato de texto decimal de dos cifras para compatibilidad con la base anterior.
- `member_accounts` relaciona integrantes con cuentas y `memberships` conserva la aprobación por iglesia.
- `office_meetings`, `office_invites` y `office_minutes` separan convocatorias, iglesias convocadas y una única acta por reunión.
- `office_plans` conserva el plan anual local. `office_campaigns` representa la recepción anual DEPEC. `office_plan_deliveries` referencia un archivo concreto e inmutable, sin apuntar implícitamente a una revisión local posterior.
- `office_credentials` relaciona una reunión con una iglesia invitada y conserva delegados, recepción y observaciones.
- `office_letters` organiza correspondencia propia y su relación opcional con una reunión de la misma organización.
- `office_templates` publica modelos comunes. `office_files` conserva cada carga como una versión nueva, con organización, autor, fecha, nombre y recurso propietario.
- `finance_projects` y `finance_categories` organizan el libro de caja. `finance_debts` conserva la obligación inicial; `finance_settlements` vincula cada pago a un único movimiento financiero.
- `finance_tokens` evita registrar dos veces un mismo envío. Los pagos utilizan una transacción `BEGIN IMMEDIATE` y validan nuevamente el saldo antes de insertarse.

## Acceso y estados

La oficina documental identifica la organización efectiva del cargo. Los cargos DEPEC no otorgan acceso al archivo de otra iglesia ni a su caja. Los líderes consultan su Secretaría; Presidencia/Vicepresidencia/Líder y Secretaría/Prosecretaría la gestionan. Tesorería se reserva a Presidencia/Vicepresidencia/Líder y Tesorería/Protesorería.

Una iglesia convocada consulta los datos de la convocatoria y su propia credencial; no recibe el acta DEPEC ni las credenciales de otras iglesias. DEPEC consulta únicamente las versiones de planes enviadas, no todos los archivos locales del remitente. Un administrador técnico conserva capacidades de soporte: no se debe usar ese rol para probar la privacidad de una directiva DEPEC.

La caja suma movimientos Aprobados. Pendientes y Anulados permanecen como detalle. Crear una deuda no afecta efectivo; pagar/cobrar inserta una liquidación y un movimiento aprobado de forma atómica. Anular ese movimiento conserva su historia y restaura el pendiente. Los pagos vinculados no se editan directamente.

Los reportes distinguen resultado filtrado de saldo general de la organización. Las deudas pendientes al cierre consideran pagos hasta esa fecha; su filtro de proyecto es independiente de las categorías de gastos. El Excel contiene valores calculados y textos tratados como datos, no fórmulas ejecutables suministradas por usuarios.

## Migración y archivos

`office_schema.sql` crea tablas e índices aditivamente. `upgrade-db` y el arranque actualizan el esquema sin borrar la base. Los movimientos anteriores se reutilizan; los documentos previos permanecen en un archivo identificado para evitar asociaciones inventadas.

Cada adjunto nuevo se valida por extensión y contenido básico, recibe un nombre aleatorio y se sirve como descarga autorizada, fuera de `static/`. Se limita el envío a 10 MB y el contenido expandido de DOCX/XLSX. Una operación fallida revierte la base y elimina únicamente los archivos nuevos de esa operación. No hay análisis antivirus integrado.

Las horas de eventos, reuniones y plazos se interpretan en America/Lima. Los plazos de recepción se comprueban en el servidor. Los permisos se vuelven a comprobar en formularios, exportaciones y descargas. La política CSP no permite handlers JavaScript inline.

## Límites operativos

No hay firma digital, correo automático, conciliación ni cierre contable inmutable. Los estados Firmada/Registrada son datos declarados por la directiva. Antes de usar información real debe validarse el flujo institucional, la operación de respaldos y el despliegue con HTTPS. Para concurrencia significativa conviene evaluar PostgreSQL.
