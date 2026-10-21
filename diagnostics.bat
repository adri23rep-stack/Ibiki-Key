@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Ibiki Key - Diagnostico completo

echo ============================================================
echo   IBIKI KEY 0.4.0 - DIAGNOSTICO
echo ============================================================
echo Carpeta: %CD%
ver
echo.

where py.exe 2>nul
where python.exe 2>nul
echo.

if not exist ".venv\Scripts\python.exe" goto missing_venv
echo [1/3] Componentes instalados
".venv\Scripts\python.exe" tools\check_runtime.py
echo.
echo [2/3] Conflictos de paquetes
".venv\Scripts\python.exe" -m pip check
echo.
echo [3/3] Prueba interna
".venv\Scripts\python.exe" tools\smoke_test.py
goto logs

:missing_venv
echo [ERROR] No existe .venv\Scripts\python.exe.
echo Ejecuta INSTALAR.bat para crear el entorno local.

:logs
echo.
if exist "data\logs\launch-error.log" (
    echo Ultimo error del lanzador grafico:
    echo ------------------------------------------------------------
    type "data\logs\launch-error.log"
    echo ------------------------------------------------------------
) else (
    echo No existe data\logs\launch-error.log.
)
echo.
echo Registro principal: data\logs\ibiki-key.log
echo Puedes copiar todo el contenido de esta ventana con clic derecho.
pause
