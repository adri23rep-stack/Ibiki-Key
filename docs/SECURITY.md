# Seguridad

## Controles incluidos

- Atajo global `Ctrl + Alt + F12` para detener remapeos, macros, lógica y acciones del mouse.
- El pánico libera teclas/botones mantenidos, cancela movimientos y restaura velocidad, doble clic y scroll capturados al iniciar el motor.
- El estado de pánico bloquea nuevas macros o pruebas lógicas hasta reanudar.
- Scripts CMD y PowerShell desactivados por perfil; el editor marca esos pasos con candado y pide autorización antes de probarlos.
- API enlazada únicamente a `127.0.0.1` y compatible con token.
- Plugins apagados hasta que el usuario los selecciona.
- Los perfiles importados pierden cambio automático, scripts y acciones externas hasta ser revisados.
- Una macro `.ibikimacro` no concede permisos: CMD y PowerShell siguen dependiendo de la autorización local del perfil receptor.
- Los archivos de macro importados tienen un límite de 5 MB y pasan por validación del modelo antes de añadirse.
- Perfiles bloqueables contra edición accidental.
- Lista blanca opcional de programas por perfil.
- Guardado atómico, copias rotativas y registro de actividad técnica.

El bloqueo de perfil de esta Alpha evita cambios accidentales; no cifra el contenido ni sustituye una contraseña de Windows.

## Recomendaciones

- No importes perfiles ni plugins de origen desconocido.
- Revisa las acciones CMD/PowerShell antes de habilitarlas.
- No abras el puerto de la API en el firewall.
- Usa administrador solo cuando la aplicación que quieres controlar también lo requiera.
- Conserva `Ctrl + Alt + F12` libre como salida de emergencia.
- Usa `Ctrl + Alt + F11` para detener una grabación de mouse sin agregar el clic de la interfaz.
