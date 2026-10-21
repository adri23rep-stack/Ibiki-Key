# Reporte de pruebas — Ibiki Key 0.4.0 Alpha Live Dashboard

Fecha: 21 de julio de 2026  
Entorno automatizado: Python 3.12.13, Linux x86_64

## Resultado

- Compilación sintáctica de `src`, `tests`, `tools` y lanzadores Python: correcta.
- Análisis estático Ruff de todo el código: correcto, sin nombres indefinidos.
- Prueba rápida del núcleo (`tools/smoke_test.py`): correcta.
- 45 pruebas independientes de la interfaz: todas correctas.
- Se incluyen 4 pruebas adicionales para el teclado completo y las tarjetas del Dashboard.
- El instalador ejecuta la suite completa de 49 pruebas después de instalar PySide6 en Windows.
- El esquema de perfiles continúa en versión 1.

Durante el análisis estático se detectó y corrigió un fallo heredado de `0.3.0`: la acción **Asignar a botón** del editor de macros del mouse utilizaba `MappingDialog` sin importarlo.

## Cobertura automatizada ejecutada

- Modelos, clonado e identidades nuevas para perfiles, macros, pasos, flujos y nodos.
- Referencias recursivas remapeadas al duplicar una macro o un flujo.
- Duración mínima/máxima de macros, incluidos azar, repeticiones e intervalos.
- Importación y exportación `.ibiki` y `.ibikimacro`.
- Historial del editor con deshacer, rehacer y conservación de rehacer tras un gesto sin cambios.
- Diagnóstico de ciclos cerrados y conexiones del flujo.
- Ramas Sí/No y espera de eventos del motor lógico.
- Monitor: historial completo, intervalo medio, pico de CPS y reinicio.
- Escritura atómica, recuperación y copias de seguridad.
- Autorización de CMD/PowerShell y comportamiento de Mod-Tap.
- API local autenticada y plugins desactivados por defecto.
- Traducción del backend nativo de mouse, incluido el botón lateral X2.
- Grabación de movimiento muestreado, botones, rueda vertical/horizontal y limpieza del clic de parada.
- Pánico del mouse: bloqueo de acciones y restauración de ajustes del sistema.
- Macros mantenidas por un botón del mouse y cancelación al soltar.
- Categoría de macro de mouse y compatibilidad con archivos anteriores.
- Lanzadores: destinos `goto`, autorreparación, versiones de Python y finales CRLF de Windows.
- Nombres de salida `0.4.0` del portable y del instalador.

Comandos utilizados:

```text
PYTHONPATH=src python tools/smoke_test.py
PYTHONPATH=src python -m unittest <45 pruebas sin interfaz>
python -m ruff check src tests tools main.py Ibiki_Key.pyw
python -m compileall -q src tests tools main.py Ibiki_Key.pyw
```

## Pruebas del Dashboard incluidas para Windows

- El teclado contiene funciones, navegación, flechas y bloque numérico completo.
- Los nombres emitidos por el hook se normalizan para activar la tecla visual correcta.
- Las macros muestran como máximo dos disparadores legibles en su tarjeta.
- Los botones laterales del mouse se muestran con nombres comprensibles.

No se ejecutaron estas cuatro pruebas en el contenedor Linux porque su imagen no contiene `libEGL.so.1`, necesaria para importar QtGui incluso sin pantalla. No se presenta el renderizado como aprobado. En Windows, `setup.bat` instala PySide6 y ahora llama a `tools\run_core_tests.py`; cualquier fallo impide que el instalador muestre **INSTALACIÓN COMPLETA**.

## No validado físicamente en esta entrega

- Renderizado final y escalado visual en monitores Windows reales.
- Animación del teclado con hooks globales en una computadora Windows.
- Arrastre real de nodos y exportación PNG desde una sesión gráfica.
- Restauración física de velocidad, doble clic y scroll mediante el pánico en Windows.
- Fidelidad de una macro grabada/reproducida con hardware de mouse real.
- Ejecución por doble clic de `setup.bat`, `run.bat` y `run_as_admin.bat`.
- Bloqueo de entradas dentro de juegos o programas elevados.
- Botones laterales de modelos concretos de mouse y brillo de monitores externos.
- Compilación con Nuitka e instalador con Inno Setup.
- Compatibilidad con sistemas anti-trampas o reglas de juegos específicos.

Estos puntos requieren una sesión real de Windows y no se presentan como aprobados.

## Límites conocidos

- Varios teclados todavía se reciben como entrada combinada.
- El botón original del mouse aún no se bloquea selectivamente.
- Anti-ghosting y Rapid Trigger físicos no pueden generarse por software.
- Integraciones directas, nube, actualización automática y más idiomas permanecen en la hoja de ruta.
