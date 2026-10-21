@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Ibiki Key 0.4.0 - Instalacion y reparacion
color 0F

set "IBIKI_NO_PAUSE=0"
if /I "%~1"=="--no-pause" set "IBIKI_NO_PAUSE=1"
set "IBIKI_STEP=busqueda de Python"

echo ============================================================
echo   IBIKI KEY 0.4.0 - INSTALACION Y REPARACION
echo ============================================================
echo Esta ventana mostrara cada paso y permanecera abierta si falla.
echo No se necesita instalar el paquete externo llamado mouse.
echo.

where py.exe >nul 2>nul
if errorlevel 1 goto try_python_path
for %%V in (3.12 3.11 3.10) do (
    py -%%V -c "import struct,sys; raise SystemExit(0 if sys.version_info[:2] in ((3,10),(3,11),(3,12)) and struct.calcsize('P') == 8 else 1)" >nul 2>nul
    if not errorlevel 1 (
        set "IBIKI_PY=py -%%V"
        goto python_ready
    )
)

:try_python_path
where python.exe >nul 2>nul
if errorlevel 1 goto try_registered_python
python.exe -c "import struct,sys; raise SystemExit(0 if sys.version_info[:2] in ((3,10),(3,11),(3,12)) and struct.calcsize('P') == 8 else 1)" >nul 2>nul
if errorlevel 1 goto try_registered_python
set "IBIKI_PY=python.exe"
goto python_ready

:try_registered_python
for /f "usebackq delims=" %%P in (`powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "tools\find_compatible_python.ps1" 2^>nul`) do (
    set IBIKI_PY="%%P"
    goto python_ready
)
goto no_python

:python_ready
echo [1/7] Python compatible encontrado:
%IBIKI_PY% --version
if errorlevel 1 goto failed

set "IBIKI_STEP=creacion del entorno aislado"
if not exist ".venv\Scripts\python.exe" goto create_venv
".venv\Scripts\python.exe" -c "import struct,sys; raise SystemExit(0 if sys.version_info[:2] in ((3,10),(3,11),(3,12)) and struct.calcsize('P') == 8 else 1)" >nul 2>nul
if not errorlevel 1 goto venv_ready
echo [2/7] El entorno anterior esta incompleto o usa otra version. Se reconstruira.
rmdir /s /q ".venv"
if exist ".venv" goto failed

:create_venv
echo [2/7] Creando el entorno aislado .venv...
%IBIKI_PY% -m venv ".venv"
if errorlevel 1 goto failed

:venv_ready
set "IBIKI_STEP=actualizacion de pip"
echo [3/7] Preparando el instalador de paquetes...
".venv\Scripts\python.exe" -m ensurepip --upgrade
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto failed

set "IBIKI_STEP=instalacion de componentes"
echo [4/7] Instalando la interfaz y los motores. Puede tardar varios minutos...
".venv\Scripts\python.exe" -m pip install --upgrade --prefer-binary --disable-pip-version-check -r requirements-runtime.txt
if not errorlevel 1 goto verify_runtime
echo.
echo [AVISO] El primer intento fallo. Reintentando sin cache...
".venv\Scripts\python.exe" -m pip install --upgrade --prefer-binary --no-cache-dir --disable-pip-version-check -r requirements-runtime.txt
if errorlevel 1 goto failed

:verify_runtime
set "IBIKI_STEP=diagnostico del entorno"
echo [5/7] Comprobando todos los componentes...
".venv\Scripts\python.exe" tools\check_runtime.py
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip check
if errorlevel 1 goto failed

set "IBIKI_STEP=prueba interna"
echo [6/7] Probando perfiles, macros y almacenamiento...
".venv\Scripts\python.exe" tools\smoke_test.py
if errorlevel 1 goto failed
".venv\Scripts\python.exe" tools\run_core_tests.py
if errorlevel 1 goto failed

set "IBIKI_STEP=prueba de interfaz"
echo [7/7] Comprobando que la ventana principal puede cargarse...
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"
".venv\Scripts\python.exe" -c "from ibiki_key.ui.main_window import MainWindow; print('[OK] Interfaz lista para iniciar')"
if errorlevel 1 goto failed

echo.
echo ============================================================
echo   INSTALACION COMPLETA
echo ============================================================
echo Haz doble clic en INICIAR.bat o run.bat.
echo Si Windows bloquea entradas globales, usa run_as_admin.bat.
if "%IBIKI_NO_PAUSE%"=="1" exit /b 0
pause
exit /b 0

:no_python
echo [ERROR] No se encontro Python 3.10, 3.11 o 3.12 de 64 bits.
echo Instala una de esas versiones y activa "Add Python to PATH".
set "IBIKI_STEP=busqueda de una version compatible de Python"
goto failed

:failed
echo.
echo ============================================================
echo   LA INSTALACION NO SE COMPLETO
echo ============================================================
echo Paso que fallo: %IBIKI_STEP%
echo Copia desde la primera linea de ERROR y ejecuta diagnostics.bat.
if "%IBIKI_NO_PAUSE%"=="1" exit /b 1
pause
exit /b 1
