@echo off
cd /d "%~dp0"
title E-Mail-Assistent – Ersteinrichtung
echo.
echo  ============================================
echo   E-Mail-Assistent – Ersteinrichtung
echo  ============================================
echo.

:: Python pruefen (py-Launcher oder python)
set PYTHON_CMD=
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
) else (
    python --version >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=python
    )
)
if "%PYTHON_CMD%"=="" (
    echo  FEHLER: Python ist nicht installiert!
    echo.
    echo  Bitte Python von https://python.org herunterladen
    echo  und installieren. Dann install.bat erneut ausfuehren.
    echo.
    pause
    exit /b 1
)

echo  Python gefunden. Erstelle virtuelle Umgebung...
%PYTHON_CMD% -m venv venv
if %errorlevel% neq 0 (
    echo  FEHLER: Virtuelle Umgebung konnte nicht erstellt werden.
    pause
    exit /b 1
)

echo  Installiere Abhaengigkeiten (dauert 1-2 Minuten)...
venv\Scripts\pip install --upgrade pip --quiet
venv\Scripts\pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo  FEHLER: Installation der Pakete fehlgeschlagen.
    echo  Bitte Internetverbindung pruefen und erneut versuchen.
    pause
    exit /b 1
)

:: Leere Datendateien anlegen
if not exist "config.json" (
    echo {} > config.json
)
if not exist "contacts.json" (
    echo [] > contacts.json
)
if not exist "style_examples" mkdir style_examples
if not exist "version.txt" (
    echo 1.0.0 > version.txt
)

echo.
echo  ============================================
echo   Installation erfolgreich!
echo  ============================================
echo.
echo  Naechste Schritte:
echo  1. Doppelklick auf "start.bat"
echo  2. Browser oeffnet sich automatisch
echo  3. Zugangsdaten in den Einstellungen eingeben
echo.
pause
