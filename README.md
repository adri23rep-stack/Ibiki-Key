# Ibiki Key 0.4.0 Alpha Live Dashboard

Ibiki Key es un remapeador y plataforma visual de automatización para Windows. Permite conectar teclas y botones con acciones, macros y flujos lógicos sin aprender un lenguaje de programación.

Esta entrega conserva Workflow Studio y Mouse Macro Studio, y agrega un Dashboard vivo inspirado en la interfaz de Nikaido. Las macros, el contexto activo y un teclado completo animado quedan reunidos sin perder las páginas especializadas.

## Novedades principales de 0.4.0

- Dashboard reorganizado en tres paneles superiores y un teclado completo en la mitad inferior.
- Panel central **Ahora** con perfil, capa, programa enfocado, estado de motores, macros, flujos, CPS/APM y última entrada → acción.
- Paneles independientes para activar, detener o probar macros de teclado y mouse sin abandonar el Dashboard.
- Teclado ISO completo con bloque de navegación, cursores y teclado numérico.
- Animación de pulsación con desvanecimiento y colores distintos para remapeos, macros, capas y teclas bloqueadas.
- Tooltips descriptivos y clic derecho sobre cualquier tecla para abrirla directamente en Remapeo.
- Barra lateral plegable que conserva iconos y deja más espacio al teclado.
- El pánico continúa desactivando macros y automatizaciones del mouse y restaurando sus ajustes originales.

## Funciones incorporadas desde 0.3.0

- Pestaña **Macros del mouse** separada de las macros generales.
- Grabación de clics, botones laterales, rueda vertical/horizontal y movimiento relativo del cursor.
- Muestreo de movimiento configurable entre 8 y 250 ms para controlar el tamaño de la secuencia.
- `Ctrl + Alt + F11` detiene la grabación sin contaminarla con el clic de la interfaz.
- Asignación directa de una macro a cualquier botón, rueda, doble toque o gesto del mouse.
- Modo **Mientras se mantiene** compatible con botones del mouse y cancelación inmediata al soltarlos.
- Pánico global que detiene macros, lógica, gestos, remapeos y movimientos en curso; libera botones mantenidos y restaura velocidad, doble clic y scroll originales de Windows.
- Instalador visible y autocurativo con selección de Python compatible, reintento sin caché, diagnóstico, `pip check`, prueba del núcleo e importación de la interfaz.
- Inicio gráfico con cuadro de error y `data\logs\launch-error.log` si la ventana no puede abrirse.

## Estado de las funciones

| Área | Estado | Incluye |
|---|---:|---|
| Teclado | Funcional | Teclas, combinaciones, bloqueo, intercambio, capas, multimedia y pausa global |
| Mouse | Funcional con límites | Backend nativo, botones, ambas ruedas, velocidad, doble clic, movimiento, gestos y restauración de emergencia |
| Macros | Funcional | Editores general y de mouse, grabación, azar, repetir, toggle, mantener, infinito e importar/exportar |
| Perfiles | Funcional | Ilimitados, cambio por programa/ventana, importar, exportar, bloquear y respaldar |
| Lógica visual | Funcional | Biblioteca, búsqueda, arrastre, conexiones Sí/No, historial, validación y PNG |
| Monitor | Funcional | Historial, filtros, CPS/APM, pico, intervalos, heatmap, copiar y CSV |
| Windows | Funcional | Abrir apps/carpetas/enlaces, texto, multimedia, volumen, brillo, captura, CMD y PowerShell |
| Gaming | Parcial | Anti rebote, Turbo, Tap Dance, Mod-Tap, perfiles por juego y modo de baja latencia |
| API | Funcional | Servidor local `127.0.0.1`, token, perfiles, macros y variables |
| Plugins | Funcional básico | Plugins Python locales, apagados por defecto y acciones registrables |
| Nube e integraciones directas | Futuro | Discord, Spotify, OBS WebSocket, Hue, MQTT, Stream Deck y perfiles en la nube |

## Inicio rápido

Necesitas Windows 10 u 11 de 64 bits y Python 3.10, 3.11 o 3.12.

1. Extrae todo el ZIP en una carpeta nueva; no ejecutes los `.bat` dentro de la vista previa del ZIP.
2. Ejecuta `INSTALAR.bat` o `setup.bat`. La ventana muestra siete verificaciones y termina con **INSTALACIÓN COMPLETA**.
3. Abre `INICIAR.bat` o `run.bat`. Si el entorno está ausente o incompleto, el mismo lanzador ejecuta la reparación y luego abre la app.
4. Para crear una secuencia del mouse, abre **Macros del mouse**, crea una macro, pulsa **Grabar en vivo** y termina con `Ctrl + Alt + F11`.
5. Usa **Asignar a botón** para enlazarla sin salir del editor.
6. Crea una asignación de teclado en **Remapeo** o abre **Lógica visual** y usa la plantilla F13 + Chrome.
7. Si una aplicación elevada no acepta el remapeo, usa `run_as_admin.bat`.

El mouse usa el backend nativo incluido; no necesita un paquete Python llamado `mouse`. Si la ventana normal no aparece, el lanzador muestra un cuadro de error; `run_console.bat` conserva la consola y `diagnostics.bat` revisa las dependencias. `repair_runtime.bat` vuelve a ejecutar la instalación visible.

El atajo de emergencia `Ctrl + Alt + F12` activa o desactiva el pánico aunque la ventana no esté visible. Al activarlo también se restauran temporalmente los ajustes originales del mouse de Windows; al reanudar se reaplican los del perfil.

## Uso del editor lógico

1. Crea o duplica un flujo.
2. Abre la pestaña **Nodos**, busca una función y arrástrala al lienzo.
3. Selecciona dos nodos con `Ctrl + clic` y pulsa **Conectar**.
4. Para una condición usa las salidas `yes` y `no`; una espera de evento puede usar `timeout`.
5. Pulsa **Validar** antes de probar. Los errores impiden ejecutar; los avisos explican riesgos o ramas incompletas.
6. Pulsa **Asignar tecla** para convertir el flujo en una automatización global.

Atajos del lienzo:

| Atajo | Función |
|---|---|
| `Ctrl + D` | Duplicar nodos seleccionados |
| `Ctrl + Z` / `Ctrl + Y` | Deshacer / rehacer |
| `Supr` | Eliminar nodos o conexiones |
| `Ctrl + 0` | Ajustar el flujo a la vista |

Los nodos muestran categoría, título, resumen e ID estable como `TRG-A1B2C3`, `CON-D4E5F6` o `ACT-123ABC`. Al duplicar varios nodos también se duplican las conexiones existentes entre ellos.

## Macros y monitor

- Las macros de mouse se guardan con su propia categoría y aparecen en una pestaña separada. Los perfiles anteriores se leen como macros generales sin migración destructiva.
- La grabación de movimiento usa desplazamientos relativos, por lo que una secuencia no depende de la resolución o posición exacta en que se grabó.
- Una macro completa se comparte desde **Exportar** y se recupera con **Importar**. El permiso para CMD/PowerShell nunca se incluye en el archivo: sigue siendo una autorización del perfil local.
- Los pasos se pueden copiar, pegar, duplicar, mover o desactivar sin borrarlos.
- Mientras se graba, la lista de macros queda bloqueada para impedir que los eventos terminen en otra macro.
- En **Monitor**, pausar detiene solamente la actualización visual; la recopilación continúa y aparece al reanudar.
- **Exportar CSV** respeta la búsqueda y los filtros activos. Usa UTF-8 con BOM y separador `;` para facilitar su apertura en Excel de Windows.

## Compilar

- `build_portable.bat`: crea una carpeta standalone y un ZIP portable con Nuitka.
- `build_installer.bat`: crea el instalador después de compilar la versión portable. Requiere Inno Setup 6.

La entrega fuente no contiene un EXE ya compilado porque la compilación debe ejecutarse en Windows. Los resultados se guardan dentro de `dist`.

## Compatibilidad

Los perfiles continúan usando el esquema 1 y se leen sin migración destructiva. Conserva la carpeta de la versión anterior como respaldo y copia/importa solamente los perfiles que quieras usar.

## Límites reales

- Un teclado normal no puede obtener Rapid Trigger físico: Ibiki solo puede reducir procesamiento y reaccionar a eventos digitales.
- El anti-ghosting depende de la matriz del teclado. Ningún programa recupera una tecla que el hardware nunca reportó.
- Varios teclados funcionan como entrada combinada. Distinguir y bloquear cada dispositivo por separado requiere Raw Input más un controlador dedicado.
- El motor detecta botones laterales y rueda horizontal, pero todavía no suprime selectivamente su acción original.
- El brillo depende del monitor y de su controlador de Windows.
- Algunos juegos competitivos prohíben macros o automatización. Respeta sus reglas y sistemas anti-trampas.
- Las integraciones directas necesitan credenciales, SDK o hardware externo; no se simulan en esta Alpha. La API local y los plugins son la base disponible.

## Seguridad y datos

- Los perfiles se guardan localmente mediante escritura atómica y hasta 20 copias automáticas.
- Las listas blancas limitan un perfil a procesos concretos.
- CMD y PowerShell están desactivados por perfil y requieren autorización explícita.
- La API escucha solamente en `127.0.0.1` y admite token.
- Los plugins ejecutan código local; activa únicamente los que provengan de una fuente confiable.
- El modo portable se controla con `portable.flag`. Sin ese archivo, los datos van a AppData.

Más información: [pruebas](TEST_REPORT.md), [cambios](CHANGELOG.md), [API](docs/API.md), [plugins](docs/PLUGINS.md), [seguridad](docs/SECURITY.md) y [arquitectura](docs/ARCHITECTURE.md).
