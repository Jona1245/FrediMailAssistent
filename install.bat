@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"
title FrediMailAssistent - Einrichtung

echo.
echo  ============================================
echo   FrediMailAssistent - Einrichtung
echo  ============================================
echo.

:: ── 1. Python suchen oder herunterladen ──────────────────────────────────
set PYTHON_CMD=
set EMBED_DIR=%~dp0python_embed
set USE_EMBED=0

if exist "%EMBED_DIR%\python.exe" (
    set PYTHON_CMD="%EMBED_DIR%\python.exe"
    set USE_EMBED=1
    echo  Python (eingebettet) gefunden.
    goto :install_packages
)

py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    echo  Python gefunden.
    goto :install_packages
)

python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    echo  Python gefunden.
    goto :install_packages
)

:: Python nicht gefunden -> automatisch herunterladen
echo  Python wird heruntergeladen (einmalig, ca. 15 MB) ...
echo.

set PY_ZIP=%~dp0_python_dl.zip
set PY_URL=https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip

powershell -NoProfile -Command "Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_ZIP%' -UseBasicParsing" 2>nul
if not exist "%PY_ZIP%" (
    echo  FEHLER: Python konnte nicht heruntergeladen werden.
    echo  Bitte Internetverbindung pruefen und erneut versuchen.
    pause
    exit /b 1
)

echo  Python wird entpackt ...
powershell -NoProfile -Command "Expand-Archive -Path '%PY_ZIP%' -DestinationPath '%EMBED_DIR%' -Force"
del "%PY_ZIP%"

:: site-packages aktivieren (benoetigt fuer pip)
for %%f in ("%EMBED_DIR%\python*._pth") do (
    powershell -NoProfile -Command "(Get-Content '%%f') -replace '#import site','import site' | Set-Content '%%f'"
)

:: pip installieren
echo  pip wird eingerichtet ...
set GET_PIP=%~dp0_getpip_dl.py
powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%GET_PIP%' -UseBasicParsing" 2>nul
if not exist "%GET_PIP%" (
    echo  FEHLER: pip konnte nicht heruntergeladen werden.
    pause
    exit /b 1
)
"%EMBED_DIR%\python.exe" "%GET_PIP%" --quiet
del "%GET_PIP%"

set PYTHON_CMD="%EMBED_DIR%\python.exe"
set USE_EMBED=1

:: ── 2. Pakete installieren ────────────────────────────────────────────────
:install_packages
echo.
echo  Pakete werden installiert (1-3 Minuten) ...

if "%USE_EMBED%"=="1" (
    "%EMBED_DIR%\python.exe" -m pip install -r requirements.txt --quiet
) else (
    if not exist venv\ (
        %PYTHON_CMD% -m venv venv
    )
    call venv\Scripts\activate.bat
    pip install --upgrade pip --quiet
    pip install -r requirements.txt --quiet
)

if %errorlevel% neq 0 (
    echo  FEHLER: Pakete konnten nicht installiert werden.
    echo  Bitte Internetverbindung pruefen und erneut versuchen.
    pause
    exit /b 1
)

:: ── 3. Datendateien anlegen ───────────────────────────────────────────────
if not exist "config.json"   echo {} > config.json
if not exist "contacts.json" echo [] > contacts.json
if not exist "style_examples" mkdir style_examples
if not exist "version.txt"   echo 1.0.0 > version.txt

:: ── 4. App-Icon (logo.ico) erstellen ─────────────────────────────────────
echo  App-Icon wird erstellt ...
if "%USE_EMBED%"=="1" (
    "%EMBED_DIR%\python.exe" create_ico.py app\static\logo.ico 2>nul
) else (
    venv\Scripts\python.exe create_ico.py app\static\logo.ico 2>nul
)

echo.
echo  ============================================
echo   Einrichtung abgeschlossen!
echo  ============================================
echo.
echo  Naechster Schritt:
echo  Doppelklick auf "Desktopverknuepfung erstellen.bat"
echo.
pause
