@echo off
setlocal
cd /d "%~dp0"
title Ibiki Key - Instalador
call setup.bat
exit /b %ERRORLEVEL%
