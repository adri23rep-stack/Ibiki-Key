@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

if not exist "dist\Ibiki_Key_Portable\IbikiKey.exe" (
    echo Primero se creará la versión portable...
    call build_portable.bat
    if errorlevel 1 exit /b 1
)

set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo [ERROR] No se encontró Inno Setup 6.
    echo Instálalo y vuelve a ejecutar este archivo.
    pause
    exit /b 1
)

"%ISCC%" "installer\Ibiki_Key.iss"
if errorlevel 1 exit /b 1
echo Instalador terminado dentro de dist.
pause
