# Historial de cambios

## 0.4.0 Alpha Live Dashboard

- Nuevo Dashboard con tres paneles superiores: macros de teclado, estado **Ahora** y macros del mouse.
- Control rápido para activar, probar y detener macros desde el inicio.
- Contexto vivo con perfil, capa, ventana activa, motores, métricas y última acción resuelta.
- Teclado virtual ISO completo, escalable y animado, incluyendo navegación, flechas y numérico.
- Leyenda y colores por tipo de asignación, tooltips y acceso directo a Remapeo con clic derecho.
- Barra lateral plegable y actualización visual sobria basada en tarjetas oscuras y violeta `#7B4DFF`.
- Se mantienen el pánico reversible, Mouse Macro Studio, Workflow Studio y el esquema de perfiles 1.

## 0.3.0 Alpha Mouse Macro Studio

- Pestaña independiente para macros del mouse con categoría persistente y compatibilidad con perfiles anteriores.
- Grabación nativa de movimiento relativo, clics, botones laterales y ruedas vertical/horizontal.
- Muestreo de movimiento configurable, límite seguro de eventos y limpieza del clic usado para detener.
- Atajo `Ctrl + Alt + F11` exclusivo para terminar una grabación de mouse.
- Asignación directa de macros a botones, rueda, doble toque y gestos.
- Macros `while_held` activadas por mouse y detención inmediata al soltar el botón.
- Pánico global ampliado a macros, lógica visual y todas las acciones del mouse.
- Captura y restauración de velocidad, intervalo de doble clic y líneas de scroll originales de Windows.
- Cancelación de movimientos interpolados y liberación de botones mantenidos al activar el pánico.
- Instalación/autorreparación en siete verificaciones y lanzador gráfico con error visible.
- Detección y remapeo de rueda horizontal.
- 44 pruebas automatizadas; esquema de perfiles conservado en versión 1.

## 0.2.0 Alpha Workflow Studio

- Biblioteca visual de nodos con búsqueda, doble clic y arrastrar al lienzo.
- Deshacer y rehacer cambios del flujo, incluidos los movimientos de nodos.
- Duplicación de nodos y flujos, menú contextual, atajos, zoom acotado y exportación PNG.
- Diagnóstico previo de conexiones inválidas, ramas incompletas, nodos inaccesibles y ciclos.
- Duplicación, activación, copia y pegado de pasos de macro.
- Importación y exportación individual de macros mediante `.ibikimacro`.
- Duración mínima/máxima estimada y destino de grabación protegido al cambiar de perfil.
- Monitor con pausa visual, filtros, selección múltiple, copiado, CSV y nuevas métricas.
- 33 pruebas automatizadas y compatibilidad conservada con perfiles de esquema 1.

## 0.1.2 Alpha Launcher Hotfix

- `run.bat` ya no confía en un `.venv` solo porque exista: primero comprueba que pueda cargar la interfaz.
- Si el entorno local está incompleto, utiliza `pyw.exe`, `pythonw.exe` o la asociación de Windows como fallback.
- Se añadió `run_console.bat`, que conserva la ventana y muestra el error completo.
- Se añadió `Ibiki_Key.pyw` como entrada directa sin consola e `install.bat` como alias sencillo del instalador.
- `setup.bat` fue simplificado y ya no oculta la salida de `pip` en un registro.
- `run_as_admin.bat` eleva el lanzador normal completo, conservando todos sus fallbacks.
- Los archivos por lotes se distribuyen con finales de línea CRLF para Windows.

## 0.1.1 Alpha Hotfix

- Se eliminó la dependencia externa `mouse`; el motor y la grabadora usan un backend nativo de Windows incluido.
- `setup.bat` muestra progreso, guarda `setup.log` y comprueba cada importación antes de declarar éxito.
- `run.bat` y `run_as_admin.bat` detectan instalaciones incompletas y ejecutan la reparación automáticamente.
- Se añadieron `repair_runtime.bat` y `diagnostics.bat`.
- Los nodos visuales ahora tienen color de categoría, etiqueta de función, ID estable, resumen y salidas visibles.
- CMD y PowerShell muestran un candado y una solicitud de autorización antes de probar la macro.
- Los bloqueos de seguridad y componentes no disponibles ya no generan trazas duplicadas como si fueran fallos inesperados.
- Se fijó una fuente base válida para evitar el aviso de Qt sobre tamaño `-1`.

## 0.1.0 Alpha

- Primera base funcional de Ibiki Key para Windows.
- Remapeo global de teclado con bloqueo opcional, combinaciones y capas.
- Remapeo de botones del mouse, scroll, cursor, doble clic y gestos.
- Macros grabadas o manuales con retrasos, azar, repetición y cancelación.
- Turbo, doble toque, anti rebote y Mod-Tap.
- Perfiles ilimitados con activación automática por proceso o ventana.
- Importación y exportación en formato `.ibiki`.
- Editor visual de lógica con condiciones Sí/No, espera de eventos y plantilla F13 + Chrome.
- Monitor de CPS, APM, intervalos, historial y heatmap.
- Acciones de Windows, variables globales, temporizadores y API local con token.
- Búsqueda de acciones, scroll horizontal y listas blancas por perfil.
- Plugins locales desactivados por defecto.
- Guardado atómico, copias automáticas y registro rotativo de errores.
