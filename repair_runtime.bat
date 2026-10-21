@echo off
setlocal
cd /d "%~dp0"
title Ibiki Key - Reparacion

echo La reparacion usara el mismo instalador visible.
echo Si .venv esta incompleto, setup.bat actualizara sus paquetes.
echo.
call setup.bat
exit /b %ERRORLEVEL%
