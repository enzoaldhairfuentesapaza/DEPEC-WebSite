# v0.4.1 — Tablón de anuncios con temporizador

## Actualizar

Detén el servidor, respalda `instance` y copia los archivos de esta entrega sobre tu proyecto, conservando `.git`, `.venv`, `instance` y tus copias. Ejecuta `iniciar.bat` y recarga con Ctrl+F5. No hace falta borrar datos ni cargar nuevamente la demo. Esta función utiliza los registros existentes y no requiere nuevas tablas.

## Crear un aviso

1. Ingresa con una cuenta de líder que tenga permiso de gestión.
2. Abre **Tablón de anuncios** en el panel.
3. Selecciona la iglesia o DEPEC en cuyo nombre publicarás.
4. Escribe el título y el mensaje.
5. Selecciona prioridad: Informativo, Importante o Urgente.
6. Define **Mostrar desde** y **Ocultar al vencer**, con fecha y hora de Perú.
7. Cambia el estado a **Publicado** y guarda.

Ejemplo para una prueba, sin afirmar una cancelación real:

- Título: «Cambio de programación · PRUEBA».
- Mensaje: «Ejemplo: esta semana se cancela el culto por elecciones; nos vemos la siguiente semana».
- Mostrar desde: la fecha y hora actuales de Perú.
- Vencimiento: el día en que el aviso deje de ser relevante.

## Comportamiento público

- El tablón aparece cerca del inicio de la portada, antes del hero.
- Cada SEC/GJ muestra solo sus anuncios. DEPEC muestra los publicados en nombre de DEPEC.
- Se muestran únicamente anuncios **Publicados** cuyo inicio ya llegó y cuyo vencimiento todavía no llegó.
- Cada mensaje muestra su prioridad, organización, fecha de vencimiento y cuenta regresiva.
- Los urgentes se ordenan primero; luego los importantes y los informativos.
- El contador usa la hora del servidor en Perú y el tiempo transcurrido en el navegador; no depende de que el visitante tenga bien ajustado su reloj.
- Si vence mientras la página está abierta, el anuncio se elimina de esa vista. Si era el último, desaparece toda la sección, incluido el título.
- Si no hay anuncios vigentes, la sección no se renderiza: no hay título ni espacio vacío.
- Sin JavaScript se muestra el tiempo restante calculado al cargar; la siguiente consulta al servidor retira los avisos vencidos.
- Un aviso programado empieza a verse al consultar o recargar la página después de su inicio. No se hace una consulta periódica para buscar nuevos avisos mientras una página permanece abierta.

## Gestión y permisos

Presidencia, vicepresidencia, secretaría, prosecretaría y el cargo genérico Líder pueden gestionar anuncios dentro de su alcance. El administrador puede gestionar todas las organizaciones. Otros cargos pueden recibir permiso adicional de edición de «Tablón de anuncios» desde Organización.

Los estados del formulario son Borrador, Publicado y Retirado. El panel muestra además el estado temporal: Programado, Vigente o Vencido. Un anuncio vencido permanece en el historial y puede editarse para reutilizarlo o retirarse; no se borra automáticamente de la base.

El final debe ser estrictamente posterior al inicio. Las fechas se interpretan en **America/Lima**. Los avisos son mensajes independientes: escribir que un culto se cancela no modifica automáticamente eventos del calendario.

No se añade un aviso ficticio por defecto: así una instalación sin avisos mantiene el tablón oculto. Las vistas estáticas regeneradas también lo omiten cuando la base de ejemplo está vacía.

## Pruebas

Se comprueban el tablón vacío, separación entre iglesias y DEPEC, horarios programados y vencidos, borradores, retiro, prioridades, validación de fechas, límites de tiempo y conservación de registros. También se comprueba la sintaxis de JavaScript. La cuenta regresiva y la retirada sin recargar necesitan revisión visual en navegador.

## GitHub

Después de copiar y probar en tu repositorio:

```powershell
git add app tests preview README.md ACTUALIZAR_v0.4.1.md docs
git commit -m "Agrega tablón de anuncios por iglesia con vigencia y cuenta regresiva"
git push origin main
```
