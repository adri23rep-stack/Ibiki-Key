@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Ibiki Key - Preparando inicio

if exist ".venv\Scripts\python.exe" if exist ".venv\Scripts\pythonw.exe" (
    ".venv\Scripts\python.exe" tools\check_runtime.py --quiet >nul 2>nul
    if not errorlevel 1 goto launch
)

echo ============================================================
echo   IBIKI KEY NECESITA PREPARAR O REPARAR SU ENTORNO
echo ============================================================
echo Se ejecutara el instalador visible y despues se abrira la app.
echo.
call setup.bat --no-pause
if errorlevel 1 goto failed

:launch
if not exist ".venv\Scripts\pythonw.exe" goto failed
start "" /D "%CD%" "%CD%\.venv\Scripts\pythonw.exe" "%CD%\Ibiki_Key.pyw"
if errorlevel 1 goto failed
exit /b 0

:failed
echo.
echo [ERROR] Ibiki Key no pudo iniciar.
echo Ejecuta diagnostics.bat o run_console.bat para ver el detalle completo.
pause
exit /b 1
