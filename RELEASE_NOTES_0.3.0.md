# Ibiki Key 0.3.0 Alpha Mouse Macro Studio

Esta versión se distribuye en una carpeta independiente y no modifica la entrega `0.2.0`.

## Instalación recomendada

1. Extrae todo el ZIP en una carpeta nueva.
2. Ejecuta `INSTALAR.bat` y espera **INSTALACIÓN COMPLETA**.
3. Abre `INICIAR.bat`.
4. Si quieres controlar un programa elevado, cierra Ibiki Key y usa `run_as_admin.bat`.

No copies `.venv` desde otra versión. El instalador local usa Python 3.10, 3.11 o 3.12 y crea su propio entorno. El mouse es nativo: instalar el paquete externo `mouse` no es necesario.

## Flujo de macros del mouse

1. Abre **Macros del mouse** y crea una macro.
2. Activa o desactiva **Grabar movimiento del cursor** y elige el muestreo.
3. Pulsa **Grabar en vivo**.
4. Realiza movimientos, clics y scroll.
5. Pulsa `Ctrl + Alt + F11` para terminar limpiamente.
6. Revisa retrasos y pasos; luego pulsa **Asignar a botón**.

## Pánico

`Ctrl + Alt + F12` detiene nuevas ejecuciones y las que estén en curso. Además de pausar los hooks, libera entradas mantenidas, cancela movimientos del cursor y restaura los valores que Windows tenía antes de iniciar el motor. El mismo atajo reanuda y reaplica el perfil.

## Diagnóstico

- `diagnostics.bat`: inventario de componentes y `pip check`.
- `run_console.bat`: inicio con traceback visible.
- `repair_runtime.bat`: reinstalación visible.
- `data\logs\launch-error.log`: error del lanzador gráfico.
- `data\logs\ibiki-key.log`: actividad de la aplicación.

La validación automatizada se ejecutó fuera de Windows. Los hooks, los `.bat` por doble clic y la restauración real de parámetros requieren comprobación en una PC Windows y no se presentan como probados físicamente.
