"""
Launcher: startet Flask und öffnet Browser.
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


def _open_browser():
    for _ in range(30):
        try:
            urllib.request.urlopen('http://localhost:5000', timeout=1)
            break
        except Exception:
            time.sleep(0.5)
    webbrowser.open('http://localhost:5000')


def main():
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
    main()
