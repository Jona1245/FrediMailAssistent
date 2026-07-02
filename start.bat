@echo off
cd /d "%~dp0"

set EMBED_DIR=%~dp0python_embed

if exist "%EMBED_DIR%\pythonw.exe" (
    start "" "%EMBED_DIR%\pythonw.exe" "%~dp0launcher.py"
    exit /b 0
)

if exist "venv\Scripts\pythonw.exe" (
    start "" "venv\Scripts\pythonw.exe" "%~dp0launcher.py"
    exit /b 0
)

echo.
echo  Bitte zuerst "Desktopverknuepfung erstellen.bat" ausfuehren!
echo.
pause
