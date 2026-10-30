# Cuenta global de pruebas — v0.5.0

## Ingresar

- Correo: `pruebas@depec.demo`
- Contraseña inicial: `DepecPruebas2026!`

Al ejecutar `iniciar.bat` después de actualizar, la cuenta se crea automáticamente si estás usando la base de demostración existente (con `admin@depec.demo`). También se incluye en instalaciones demo nuevas. No se reemplazan contraseñas de cuentas existentes ni se convierte en administrador un usuario ajeno que ya use ese correo.

## Cambiar de rol

1. Inicia sesión con la cuenta global de pruebas.
2. Abre el selector flotante **PRUEBAS**, cerca de la esquina superior derecha.
3. Elige DEPEC o una SEC/GJ.
4. Elige un rol y pulsa **Aplicar rol**.

Opciones: Administrador, Presidente, Vicepresidente, Secretario, Prosecretario, Tesorero, Protesorero, Vocal, Asesor, Líder, Miembro y Visitante.

- Administrador permite probar la gestión global.
- Un cargo en una iglesia usa el alcance y permisos de esa iglesia.
- Un cargo en DEPEC usa el alcance real que ya tiene ese cargo en el sistema.
- Miembro crea una identidad de prueba con registro aprobado en la SEC/GJ elegida, sin permisos de líder. Puede probar su portal, perfil y revisión de publicaciones. DEPEC no acepta este modo de miembro porque no es una iglesia.
- Visitante permite ver el sitio sin usuario efectivo autenticado. El selector conserva la sesión del operador para que puedas regresar a otro rol.

El selector permanece disponible en las páginas de acceso restringido. Puedes volver a Administrador sin introducir otra vez la contraseña. **Cerrar sesión de pruebas** termina tanto la identidad seleccionada como la sesión del operador.

## Qué ocurre con los permisos y los datos

El sistema usa identidades de prueba separadas para cada combinación de iglesia y rol; no toma la identidad de una persona real. No conserva el permiso de administrador al pasar a otro rol. Estas identidades tienen contraseña aleatoria no mostrada y no se publican como directivos o miembros automáticamente.

Al volver a la misma combinación se reutiliza su identidad; no se crean cuentas duplicadas. Se restablece el permiso base del cargo, desactivando concesiones adicionales que se hubieran añadido a esa identidad de prueba. Los registros de personas reales no se modifican al cambiar de rol. Los cambios de rol se anotan en el historial.

**Las operaciones que guardes sí cambian los datos de la base que estás probando**: eventos, fotos, finanzas, aprobaciones, etc. El selector cambia permisos; no convierte las escrituras en simulaciones. Todas las pestañas del mismo navegador comparten el rol; después de cambiarlo, recarga otras pestañas para renovar sus formularios.

## Si tu base no es una demo

No se crea automáticamente una cuenta global de pruebas en una instalación sin los datos demo. Para crearla explícitamente:

```powershell
.\.venv\Scripts\python.exe -m flask --app run create-test-user
```

El comando solicita y confirma una contraseña de al menos 12 caracteres. Usa `pruebas@depec.demo` por defecto; puedes elegir otro correo con `--email`. No restablece la contraseña de una cuenta ya creada.

Al terminar las pruebas puedes desactivar la cuenta desde **Grupos y directivas → Cuentas de acceso**, usando tu administrador habitual. Al desactivarla, también deja de funcionar cualquier sesión suya que estuviera usando otro rol.

## Actualizar

Conserva `instance`, `.venv`, `.git` y tus respaldos al copiar esta entrega. Ejecuta `iniciar.bat` y recarga con Ctrl+F5. Las tablas del laboratorio se añaden sin borrar datos. No ejecutes `init-db` sobre tu base existente.

## Verificación

Se comprueban cambios de rol sin privilegios residuales, alcance por iglesia y DEPEC, modo miembro y visitante, regreso a administrador, CSRF, validación de rol/organización, reutilización de identidades y revocación de la sesión al desactivar al operador. La comprobación de interfaz se realiza en DOM simulado; falta la revisión visual en un navegador real.
