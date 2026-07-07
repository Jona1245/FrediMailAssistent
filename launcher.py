"""
Launcher: startet Flask und öffnet Browser.
Fehler werden in start_fehler.log geschrieben und als Popup angezeigt
(wichtig, weil pythonw.exe keine Konsole hat und sonst still stirbt).
"""
import os
import sys
import time
import threading
import webbrowser
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE, 'app')
VERSION_FILE = os.path.join(BASE, 'version.txt')
ERROR_LOG = os.path.join(BASE, 'start_fehler.log')
URL = 'http://127.0.0.1:5000'

# Expose paths so the in-app updater can restart the process
os.environ['FREDI_BASE'] = BASE
os.environ['FREDI_LAUNCHER'] = os.path.abspath(__file__)
os.environ['FREDI_PYTHON'] = sys.executable


def _current_version():
    try:
        with open(VERSION_FILE, 'r') as f:
            return f.read().strip()
    except Exception:
        return '0.0.0'


def _server_responds(timeout=1):
    try:
        urllib.request.urlopen(URL, timeout=timeout)
        return True
    except Exception:
        return False


def _open_browser():
    for _ in range(30):
        if _server_responds():
            break
        time.sleep(0.5)
    webbrowser.open(URL)


def _show_error(text):
    try:
        with open(ERROR_LOG, 'w', encoding='utf-8') as f:
            f.write(text)
    except Exception:
        pass
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            'FrediMailAssistent konnte nicht starten.\n\n'
            + text[-1200:]
            + f'\n\nDetails: {ERROR_LOG}',
            'FrediMailAssistent – Fehler',
            0x10,  # MB_ICONERROR
        )
    except Exception:
        print(text)


def main():
    # Läuft die App schon (z.B. Doppelklick zweimal)? Dann nur Browser öffnen.
    if _server_responds():
        webbrowser.open(URL)
        return

    print('=' * 50)
    print('  E-Mail-Assistent – SunProPower')
    print(f'  Version: {_current_version()}')
    print('=' * 50)
    print()

    threading.Thread(target=_open_browser, daemon=True).start()

    sys.path.insert(0, APP_DIR)
    from main import app
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        _show_error(traceback.format_exc())
        sys.exit(1)
