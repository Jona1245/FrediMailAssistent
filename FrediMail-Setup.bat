@echo off
setlocal
title FrediMailAssistent - Einrichtung

set "INSTALL_DIR=%USERPROFILE%\FrediMailAssistent"
set "EMBED_DIR=%INSTALL_DIR%\python_embed"
set "ZIP_URL=https://github.com/Jona1245/FrediMailAssistent/archive/refs/heads/master.zip"
set "ZIP_FILE=%TEMP%\FrediMail_setup.zip"
set "TMP_DIR=%TEMP%\FrediMail_extract"
set "BK_DIR=%TEMP%\FrediMail_backup"
set "LOG=%TEMP%\FrediMail_install_log.txt"
set "PS=powershell -NoProfile -ExecutionPolicy Bypass -Command"

echo FrediMailAssistent Installations-Log > "%LOG%"

echo.
echo  ============================================
echo   FrediMailAssistent - Einrichtung
echo  ============================================
echo.
echo  Laeuft automatisch durch (ca. 2-5 Minuten).
echo  Fenster bitte NICHT schliessen!
echo.

echo  [1/5] Programm herunterladen ...
if exist "%ZIP_FILE%" del /q "%ZIP_FILE%" >nul 2>&1
%PS% "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%ZIP_URL%' -OutFile '%ZIP_FILE%' -UseBasicParsing" >>"%LOG%" 2>&1
if not exist "%ZIP_FILE%" goto :err_download

echo  [2/5] Entpacken ...

rem -- Zugangsdaten sichern, falls schon installiert (Update) --
if exist "%BK_DIR%" rmdir /s /q "%BK_DIR%" >nul 2>&1
mkdir "%BK_DIR%" >nul 2>&1
if exist "%INSTALL_DIR%\config.json"   copy /y "%INSTALL_DIR%\config.json"   "%BK_DIR%\" >nul 2>&1
if exist "%INSTALL_DIR%\config.key"    copy /y "%INSTALL_DIR%\config.key"    "%BK_DIR%\" >nul 2>&1
if exist "%INSTALL_DIR%\contacts.json" copy /y "%INSTALL_DIR%\contacts.json" "%BK_DIR%\" >nul 2>&1
if exist "%INSTALL_DIR%\style_examples" xcopy /e /i /q /y "%INSTALL_DIR%\style_examples" "%BK_DIR%\style_examples" >nul 2>&1

if exist "%TMP_DIR%" rmdir /s /q "%TMP_DIR%" >nul 2>&1
%PS% "Expand-Archive -Path '%ZIP_FILE%' -DestinationPath '%TMP_DIR%' -Force" >>"%LOG%" 2>&1
del /q "%ZIP_FILE%" >nul 2>&1
if not exist "%TMP_DIR%" goto :err_extract

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
for /d %%S in ("%TMP_DIR%\*") do xcopy /e /i /q /y "%%S\*" "%INSTALL_DIR%\" >>"%LOG%" 2>&1
rmdir /s /q "%TMP_DIR%" >nul 2>&1
if not exist "%INSTALL_DIR%\launcher.py" goto :err_extract

rem -- Zugangsdaten wiederherstellen --
if exist "%BK_DIR%\config.json"   copy /y "%BK_DIR%\config.json"   "%INSTALL_DIR%\" >nul 2>&1
if exist "%BK_DIR%\config.key"    copy /y "%BK_DIR%\config.key"    "%INSTALL_DIR%\" >nul 2>&1
if exist "%BK_DIR%\contacts.json" copy /y "%BK_DIR%\contacts.json" "%INSTALL_DIR%\" >nul 2>&1
if exist "%BK_DIR%\style_examples" xcopy /e /i /q /y "%BK_DIR%\style_examples" "%INSTALL_DIR%\style_examples" >nul 2>&1
rmdir /s /q "%BK_DIR%" >nul 2>&1

if not exist "%INSTALL_DIR%\config.json"   echo {}> "%INSTALL_DIR%\config.json"
if not exist "%INSTALL_DIR%\contacts.json" echo []> "%INSTALL_DIR%\contacts.json"
if not exist "%INSTALL_DIR%\style_examples" mkdir "%INSTALL_DIR%\style_examples"

echo  [3/5] Python einrichten ...
set "PYEXE="
set "PYW="
set "SYSPY="

rem -- schon vorhanden von frueherer Installation? --
if exist "%INSTALL_DIR%\venv\Scripts\python.exe" (
    set "PYEXE=%INSTALL_DIR%\venv\Scripts\python.exe"
    set "PYW=%INSTALL_DIR%\venv\Scripts\pythonw.exe"
    goto :packages
)
if exist "%EMBED_DIR%\python.exe" (
    set "PYEXE=%EMBED_DIR%\python.exe"
    set "PYW=%EMBED_DIR%\pythonw.exe"
    goto :packages
)

rem -- System-Python suchen --
py -3 --version >nul 2>&1
if not errorlevel 1 set "SYSPY=py -3"
if defined SYSPY goto :make_venv
python --version >nul 2>&1
if not errorlevel 1 set "SYSPY=python"
if defined SYSPY goto :make_venv

rem -- kein Python: eingebettetes Python automatisch herunterladen --
echo         Python wird heruntergeladen (ca. 11 MB) ...
%PS% "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip' -OutFile '%TEMP%\FrediMail_py.zip' -UseBasicParsing" >>"%LOG%" 2>&1
if not exist "%TEMP%\FrediMail_py.zip" goto :err_python
%PS% "Expand-Archive -Path '%TEMP%\FrediMail_py.zip' -DestinationPath '%EMBED_DIR%' -Force" >>"%LOG%" 2>&1
del /q "%TEMP%\FrediMail_py.zip" >nul 2>&1
if not exist "%EMBED_DIR%\python.exe" goto :err_python
%PS% "Get-ChildItem '%EMBED_DIR%\python*._pth' | ForEach-Object { (Get-Content $_.FullName) -replace '#import site','import site' | Set-Content $_.FullName }" >>"%LOG%" 2>&1
echo         pip wird eingerichtet ...
%PS% "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%TEMP%\FrediMail_getpip.py' -UseBasicParsing" >>"%LOG%" 2>&1
if not exist "%TEMP%\FrediMail_getpip.py" goto :err_python
"%EMBED_DIR%\python.exe" "%TEMP%\FrediMail_getpip.py" --no-warn-script-location >>"%LOG%" 2>&1
del /q "%TEMP%\FrediMail_getpip.py" >nul 2>&1
set "PYEXE=%EMBED_DIR%\python.exe"
set "PYW=%EMBED_DIR%\pythonw.exe"
goto :packages

:make_venv
echo         Virtuelle Umgebung wird erstellt ...
%SYSPY% -m venv "%INSTALL_DIR%\venv" >>"%LOG%" 2>&1
if not exist "%INSTALL_DIR%\venv\Scripts\python.exe" goto :err_python
set "PYEXE=%INSTALL_DIR%\venv\Scripts\python.exe"
set "PYW=%INSTALL_DIR%\venv\Scripts\pythonw.exe"

:packages
echo  [4/5] Pakete installieren (1-3 Minuten) ...
"%PYEXE%" -m pip install -r "%INSTALL_DIR%\requirements.txt" --no-warn-script-location >>"%LOG%" 2>&1
"%PYEXE%" -c "import flask, imapclient, anthropic, google.generativeai, cryptography, PIL, requests" >>"%LOG%" 2>&1
if errorlevel 1 goto :err_pip

echo  [5/5] Desktop-Symbol erstellen und App starten ...
set "ICON=%INSTALL_DIR%\app\static\logo.ico"
"%PYEXE%" "%INSTALL_DIR%\create_ico.py" "%ICON%" >>"%LOG%" 2>&1

%PS% "$ws=New-Object -ComObject WScript.Shell; $d=[Environment]::GetFolderPath('Desktop'); $lnk=Join-Path $d 'FrediMailAssistent.lnk'; $s=$ws.CreateShortcut($lnk); $s.TargetPath='%PYW%'; $s.Arguments='\"%INSTALL_DIR%\launcher.py\"'; $s.IconLocation='%ICON%'; $s.WorkingDirectory='%INSTALL_DIR%'; $s.Description='FrediMailAssistent starten'; $s.Save(); if (Test-Path $lnk) { exit 0 } else { exit 1 }" >>"%LOG%" 2>&1
if errorlevel 1 echo         Hinweis: Desktop-Symbol konnte nicht erstellt werden.

start "" "%PYW%" "%INSTALL_DIR%\launcher.py"
%PS% "for($i=0;$i -lt 45;$i++){ try { Invoke-WebRequest 'http://127.0.0.1:5000' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { Start-Sleep -Milliseconds 700 } }; exit 1" >>"%LOG%" 2>&1
if errorlevel 1 goto :err_start

echo.
echo  ============================================
echo   FERTIG!
echo.
echo   Die App laeuft - der Browser oeffnet
echo   sich gleich von selbst.
echo.
echo   Ab jetzt einfach: Doppelklick auf das
echo   gruene Desktop-Symbol FrediMailAssistent
echo  ============================================
echo.
pause
exit /b 0

:err_download
echo.
echo  FEHLER: Download fehlgeschlagen.
echo  Bitte Internetverbindung pruefen und die Datei
echo  erneut doppelklicken. Details im Log (oeffnet sich).
start notepad "%LOG%"
pause
exit /b 1

:err_extract
echo.
echo  FEHLER: Entpacken fehlgeschlagen.
echo  Details im Log (oeffnet sich).
start notepad "%LOG%"
pause
exit /b 1

:err_python
echo.
echo  FEHLER: Python konnte nicht eingerichtet werden.
echo  Details im Log (oeffnet sich).
start notepad "%LOG%"
pause
exit /b 1

:err_pip
echo.
echo  FEHLER: Programmpakete konnten nicht installiert
echo  werden. Bitte Internetverbindung pruefen und die
echo  Datei erneut doppelklicken. Details im Log.
start notepad "%LOG%"
pause
exit /b 1

:err_start
echo.
echo  Die Einrichtung ist fertig, aber die App hat nicht
echo  innerhalb von 30 Sekunden geantwortet.
echo  Bitte das Desktop-Symbol doppelklicken. Falls eine
echo  Fehlermeldung erscheint, diese bitte weitergeben.
if exist "%INSTALL_DIR%\start_fehler.log" start notepad "%INSTALL_DIR%\start_fehler.log"
pause
exit /b 1
