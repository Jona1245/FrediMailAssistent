@echo off
chcp 65001 >nul
cd /d "%~dp0"
title FrediMailAssistent - Desktop-Symbol erstellen

echo.
echo  ============================================
echo   FrediMailAssistent - Desktop-Symbol
echo  ============================================
echo.

:: Einrichten falls noch nicht geschehen
set EMBED_DIR=%~dp0python_embed
if not exist "%EMBED_DIR%\python.exe" (
    if not exist "venv\Scripts\python.exe" (
        echo  Erste Einrichtung laeuft ...
        echo.
        call "%~dp0install.bat"
    )
)

:: pythonw.exe bestimmen (kein Terminalfenster beim Start)
set PYTHONW=
if exist "%EMBED_DIR%\pythonw.exe" set PYTHONW=%EMBED_DIR%\pythonw.exe
if "%PYTHONW%"=="" if exist "%~dp0venv\Scripts\pythonw.exe" set PYTHONW=%~dp0venv\Scripts\pythonw.exe

:: Desktop-Symbol erstellen
set ICON=%~dp0app\static\logo.ico
set LAUNCHER=%~dp0launcher.py
set LNK=%USERPROFILE%\Desktop\FrediMailAssistent.lnk
set WORKDIR=%~dp0

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $s = $ws.CreateShortcut('%LNK%'); ^
   $s.TargetPath = '%PYTHONW%'; ^
   $s.Arguments = '\"%LAUNCHER%\"'; ^
   $s.IconLocation = '%ICON%'; ^
   $s.WorkingDirectory = '%WORKDIR%'; ^
   $s.WindowStyle = 1; ^
   $s.Description = 'FrediMailAssistent starten'; ^
   $s.Save()"

if exist "%LNK%" (
    echo.
    echo  Fertig! Das Symbol "FrediMailAssistent" ist jetzt auf dem Desktop.
    echo  Ab sofort einfach per Doppelklick auf das gruene Symbol starten.
    echo.
) else (
    echo.
    echo  Fehler: Symbol konnte nicht erstellt werden.
    echo  Bitte als Administrator ausfuehren.
    echo.
)
pause
