@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv-build\Scripts\python.exe" (
    where py >nul 2>nul
    if not errorlevel 1 goto :build_with_py
    where python >nul 2>nul
    if errorlevel 1 goto :no_python
    python -m venv .venv-build
    goto :venv_created
)
goto :venv_ready

:build_with_py
py -3 -m venv .venv-build
goto :venv_created

:no_python
echo [ERROR] No se encontró Python.
goto :failed

:venv_created
if errorlevel 1 goto :failed

:venv_ready

echo Instalando herramientas de compilación...
".venv-build\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :failed
".venv-build\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 goto :failed

if exist "build\main.dist" rmdir /s /q "build\main.dist"
if exist "dist\Ibiki_Key_Portable" rmdir /s /q "dist\Ibiki_Key_Portable"

echo Compilando Ibiki Key en modo standalone...
".venv-build\Scripts\python.exe" -m nuitka ^
  --mode=standalone ^
  --output-dir=build ^
  --output-filename=IbikiKey.exe ^
  --remove-output ^
  --assume-yes-for-downloads ^
  --enable-plugins=pyside6 ^
  --windows-console-mode=disable ^
  --windows-icon-from-ico=assets\ibiki-key.ico ^
  --include-data-dir=assets=assets ^
  --include-data-file=portable.flag=portable.flag ^
  --company-name="Team Nikaido" ^
  --product-name="Ibiki Key" ^
  --file-description="Ibiki Key Visual Input Automation" ^
  --file-version=0.4.0.0 ^
  --product-version=0.4.0.0 ^
  --copyright="Copyright Team Nikaido" ^
  main.py
if errorlevel 1 goto :failed

mkdir "dist\Ibiki_Key_Portable" 2>nul
xcopy "build\main.dist\*" "dist\Ibiki_Key_Portable\" /E /I /Y >nul
copy /Y "README.md" "dist\Ibiki_Key_Portable\README.md" >nul
copy /Y "LICENSE.txt" "dist\Ibiki_Key_Portable\LICENSE.txt" >nul

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "if(Test-Path 'dist\Ibiki_Key-0.4.0-Alpha-Live-Dashboard-Portable.zip'){Remove-Item 'dist\Ibiki_Key-0.4.0-Alpha-Live-Dashboard-Portable.zip'}; Compress-Archive -Path 'dist\Ibiki_Key_Portable\*' -DestinationPath 'dist\Ibiki_Key-0.4.0-Alpha-Live-Dashboard-Portable.zip' -CompressionLevel Optimal"
if errorlevel 1 goto :failed

echo.
echo Compilación terminada:
echo dist\Ibiki_Key-0.4.0-Alpha-Live-Dashboard-Portable.zip
pause
exit /b 0

:failed
echo.
echo [ERROR] La compilación falló. Revisa el mensaje anterior.
pause
exit /b 1
