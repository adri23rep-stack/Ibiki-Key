@echo off
setlocal
cd /d "%~dp0"
title Ibiki Key - Solicitud de administrador

set "IBIKI_RUN=%CD%\run.bat"
echo Windows mostrara la confirmacion de administrador.
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; try { $a='/c '+[char]34+$env:IBIKI_RUN+[char]34; Start-Process -FilePath $env:ComSpec -ArgumentList $a -Verb RunAs; exit 0 } catch { Write-Host $_.Exception.Message; exit 1 }"
if errorlevel 1 goto failed
exit /b 0

:failed
echo.
echo [ERROR] Windows cancelo o rechazo el inicio como administrador.
pause
exit /b 1
