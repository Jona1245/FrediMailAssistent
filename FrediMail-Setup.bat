@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title FrediMailAssistent – Einrichtung
cls

echo.
echo  ============================================
echo   FrediMailAssistent – Automatische
echo   Einrichtung (einmalig)
echo  ============================================
echo.
echo  Bitte warten – Fenster NICHT schliessen!
echo.

set "INSTALL_DIR=%USERPROFILE%\FrediMailAssistent"
set "EMBED_DIR=%INSTALL_DIR%\python_embed"
set "ZIP_URL=https://github.com/Jona1245/FrediMailAssistent/archive/refs/tags/v1.3.2.zip"
set "ZIP_FILE=%TEMP%\FrediMail_setup.zip"
set "TMP_DIR=%TEMP%\FrediMail_extract"
set "BK_DIR=%TEMP%\FrediMail_backup_%RANDOM%"
set "EMBED_EXISTS=0"
set "VENV_EXISTS=0"

:: ─ 1. Herunterladen ──────────────────────────────────────────────────────────
echo  [1/4]  Programm herunterladen ...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Invoke-WebRequest -Uri '%ZIP_URL%' -OutFile '%ZIP_FILE%' -UseBasicParsing"

if not exist "%ZIP_FILE%" (
    echo.
    echo  FEHLER: Download fehlgeschlagen.
    echo  Bitte Internetverbindung pruefen und
    echo  diese Datei erneut doppelklicken.
    echo.
    pause & exit /b 1
)

:: ─ 2. Entpacken (Zugangsdaten sichern falls Update) ─────────────────────────
echo  [2/4]  Entpacken ...

if exist "%INSTALL_DIR%\config.json" (
    mkdir "%BK_DIR%" >nul 2>&1
    copy /y "%INSTALL_DIR%\config.json"   "%BK_DIR%\" >nul 2>&1
    copy /y "%INSTALL_DIR%\config.key"    "%BK_DIR%\" >nul 2>&1
    copy /y "%INSTALL_DIR%\contacts.json" "%BK_DIR%\" >nul 2>&1
    if exist "%INSTALL_DIR%\style_examples" (
        xcopy /e /i /q "%INSTALL_DIR%\style_examples\*" "%BK_DIR%\style_examples\" >nul 2>&1
    )
    if exist "%EMBED_DIR%\python.exe"             set "EMBED_EXISTS=1"
    if exist "%INSTALL_DIR%\venv\Scripts\python.exe" set "VENV_EXISTS=1"
)

if exist "%TMP_DIR%" rmdir /s /q "%TMP_DIR%"
mkdir "%TMP_DIR%" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Expand-Archive -Path '%ZIP_FILE%' -DestinationPath '%TMP_DIR%' -Force"
del "%ZIP_FILE%" >nul 2>&1

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
for /d %%S in ("%TMP_DIR%\*") do xcopy /e /i /q "%%S\*" "%INSTALL_DIR%\" >nul
rmdir /s /q "%TMP_DIR%" >nul 2>&1

:: Zugangsdaten wiederherstellen
if exist "%BK_DIR%\config.json"   copy /y "%BK_DIR%\config.json"   "%INSTALL_DIR%\" >nul 2>&1
if exist "%BK_DIR%\config.key"    copy /y "%BK_DIR%\config.key"    "%INSTALL_DIR%\" >nul 2>&1
if exist "%BK_DIR%\contacts.json" copy /y "%BK_DIR%\contacts.json" "%INSTALL_DIR%\" >nul 2>&1
if exist "%BK_DIR%\style_examples" (
    xcopy /e /i /q "%BK_DIR%\style_examples\*" "%INSTALL_DIR%\style_examples\" >nul 2>&1
)
if exist "%BK_DIR%" rmdir /s /q "%BK_DIR%" >nul 2>&1

:: Leere Datendateien anlegen (Erstinstallation)
if not exist "%INSTALL_DIR%\config.json"   echo {} > "%INSTALL_DIR%\config.json"
if not exist "%INSTALL_DIR%\contacts.json" echo [] > "%INSTALL_DIR%\contacts.json"
if not exist "%INSTALL_DIR%\style_examples" mkdir "%INSTALL_DIR%\style_examples"

:: ─ 3. Python + Pakete ────────────────────────────────────────────────────────
echo  [3/4]  Python und Pakete einrichten (1-3 Minuten) ...

set "PYTHONW="

if "%EMBED_EXISTS%"=="1" (
    "%EMBED_DIR%\python.exe" -m pip install -r "%INSTALL_DIR%\requirements.txt" --quiet
    set "PYTHONW=%EMBED_DIR%\pythonw.exe"
    goto :make_icon
)

if "%VENV_EXISTS%"=="1" (
    call "%INSTALL_DIR%\venv\Scripts\activate.bat"
    pip install --upgrade pip --quiet
    pip install -r "%INSTALL_DIR%\requirements.txt" --quiet
    set "PYTHONW=%INSTALL_DIR%\venv\Scripts\pythonw.exe"
    goto :make_icon
)

:: Frische Installation – Python suchen
py --version >nul 2>&1
if %errorlevel% equ 0 ( set "_PY=py"     & goto :use_system_python )
python --version >nul 2>&1
if %errorlevel% equ 0 ( set "_PY=python" & goto :use_system_python )

:: Kein Python gefunden – embedded herunterladen
echo    Python nicht gefunden.
echo    Wird automatisch heruntergeladen (ca. 15 MB) ...
set "PY_ZIP=%TEMP%\py_embed_%RANDOM%.zip"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip' -OutFile '%PY_ZIP%' -UseBasicParsing"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Expand-Archive -Path '%PY_ZIP%' -DestinationPath '%EMBED_DIR%' -Force"
del "%PY_ZIP%" >nul 2>&1
for %%f in ("%EMBED_DIR%\python*._pth") do (
    powershell -NoProfile -Command "(Get-Content '%%f') -replace '#import site','import site' | Set-Content '%%f'"
)
set "PY_GETPIP=%TEMP%\get-pip_%RANDOM%.py"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%PY_GETPIP%' -UseBasicParsing"
"%EMBED_DIR%\python.exe" "%PY_GETPIP%" --quiet
del "%PY_GETPIP%" >nul 2>&1
"%EMBED_DIR%\python.exe" -m pip install -r "%INSTALL_DIR%\requirements.txt" --quiet
set "PYTHONW=%EMBED_DIR%\pythonw.exe"
goto :make_icon

:use_system_python
if not exist "%INSTALL_DIR%\venv" %_PY% -m venv "%INSTALL_DIR%\venv"
call "%INSTALL_DIR%\venv\Scripts\activate.bat"
pip install --upgrade pip --quiet
pip install -r "%INSTALL_DIR%\requirements.txt" --quiet
set "PYTHONW=%INSTALL_DIR%\venv\Scripts\pythonw.exe"

:make_icon
:: ─ 4. Icon + Desktop-Symbol ──────────────────────────────────────────────────
echo  [4/4]  Desktop-Symbol erstellen ...

set "ICON=%INSTALL_DIR%\app\static\logo.ico"

if exist "%PYTHONW%" (
    "%PYTHONW%" "%INSTALL_DIR%\create_ico.py" "%ICON%" >nul 2>&1
)
if not exist "%ICON%" (
    :: Fallback mit python.exe (mit Konsolenfenster, wird aber sofort geschlossen)
    for %%p in (
        "%INSTALL_DIR%\venv\Scripts\python.exe"
        "%EMBED_DIR%\python.exe"
    ) do (
        if exist %%p (
            %%p "%INSTALL_DIR%\create_ico.py" "%ICON%" >nul 2>&1
            goto :create_lnk
        )
    )
)

:create_lnk
set "LAUNCHER=%INSTALL_DIR%\launcher.py"
set "LNK=%USERPROFILE%\Desktop\FrediMailAssistent.lnk"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $s = $ws.CreateShortcut('%LNK%'); ^
   $s.TargetPath = '%PYTHONW%'; ^
   $s.Arguments = '\"%LAUNCHER%\"'; ^
   $s.IconLocation = '%ICON%'; ^
   $s.WorkingDirectory = '%INSTALL_DIR%'; ^
   $s.WindowStyle = 1; ^
   $s.Description = 'FrediMailAssistent starten'; ^
   $s.Save()"

:: ─ Fertig ────────────────────────────────────────────────────────────────────
echo.
if exist "%LNK%" (
    echo  ============================================
    echo   Fertig!
    echo.
    echo   Das gruene Symbol "FrediMailAssistent"
    echo   ist jetzt auf Ihrem Desktop.
    echo.
    echo   Einfach doppelklicken und loslegen!
    echo  ============================================
) else (
    echo  HINWEIS: Symbol konnte nicht automatisch
    echo  erstellt werden.
    echo  Bitte als Administrator ausfuehren oder
    echo  manuell starten: %INSTALL_DIR%\start.bat
)
echo.
pause
endlocal
