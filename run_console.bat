@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Ibiki Key - Inicio con diagnostico visible

echo ============================================================
echo   IBIKI KEY - INICIO CON CONSOLA
echo ============================================================
echo Esta ventana permanecera abierta y mostrara cualquier error.
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" tools\check_runtime.py --quiet >nul 2>nul
    if not errorlevel 1 goto launch
)

echo [AVISO] El entorno no esta listo. Ejecutando reparacion...
call setup.bat --no-pause
if errorlevel 1 goto failed

:launch
echo Usando: %CD%\.venv\Scripts\python.exe
echo.
".venv\Scripts\python.exe" main.py
set "IBIKI_EXIT=%ERRORLEVEL%"
echo.
echo Ibiki Key termino con codigo: %IBIKI_EXIT%
pause
exit /b %IBIKI_EXIT%

:failed
echo.
echo [ERROR] No se pudo preparar el entorno de Ibiki Key.
echo Ejecuta diagnostics.bat y copia su salida.
pause
exit /b 1
