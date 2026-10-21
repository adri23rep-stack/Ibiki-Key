# Notas de la revisión 0.1.2

Esta revisión conserva el backend de mouse y los nodos rediseñados de `0.1.1`, y corrige sus lanzadores de Windows.

## Actualización recomendada

1. Conserva la carpeta de `0.1.0` como respaldo.
2. Extrae esta revisión en una carpeta nueva.
3. Ejecuta `setup.bat` y espera el mensaje **LISTO**.
4. Abre la interfaz con `run.bat`; si falla, abre `run_console.bat` para conservar el mensaje exacto.
5. Exporta los perfiles que quieras conservar desde la versión anterior e impórtalos en esta revisión.

El formato `.ibiki` y el esquema de perfiles no cambiaron. No copies `.venv` desde la versión anterior; el entorno de esta revisión ya no necesita el paquete externo `mouse`.

## Si la interfaz no aparece

- Ejecuta `diagnostics.bat` para conocer el componente exacto que falta.
- Ejecuta `repair_runtime.bat` para reinstalar los componentes declarados.
- Consulta `setup.log`, `repair-runtime.log` y `data\logs\ibiki-key.log`.
- Usa `run_as_admin.bat` solo cuando necesites controlar otra aplicación elevada.

## CMD y PowerShell

El candado no es un fallo. Los comandos están desactivados por seguridad. Al pulsar **Probar** en una macro que los contenga, Ibiki Key muestra qué se va a autorizar y pide confirmación para ese perfil.
