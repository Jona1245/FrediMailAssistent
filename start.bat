@echo off
cd /d "%~dp0"

set EMBED_DIR=%~dp0python_embed

if exist "%EMBED_DIR%\python.exe" (
    start "FrediMailAssistent" /min cmd /c ""%EMBED_DIR%\python.exe" launcher.py"
    exit /b 0
)

if exist "venv\Scripts\python.exe" (
    start "FrediMailAssistent" /min cmd /c "venv\Scripts\python.exe launcher.py"
    exit /b 0
)

echo.
echo  Bitte zuerst "Desktopverknuepfung erstellen.bat" ausfuehren!
echo.
pause
