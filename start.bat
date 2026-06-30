@echo off
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo.
    echo  FEHLER: Virtuelle Umgebung nicht gefunden.
    echo  Bitte zuerst "install.bat" ausfuehren!
    echo.
    pause
    exit /b 1
)

start "E-Mail-Assistent" /min cmd /c "venv\Scripts\python.exe launcher.py & pause"
