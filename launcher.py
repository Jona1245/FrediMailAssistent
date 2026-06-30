"""
Launcher: prüft auf Updates, startet Flask, öffnet Browser.
Fredi startet dies über start.bat — er sieht nur den Browser.
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

# ── GitHub Update-Konfiguration ───────────────────────────────────────────────
# Trage hier dein GitHub-Repo und einen read-only Personal Access Token ein.
# Lasse GITHUB_TOKEN leer ("") um Updates zu deaktivieren.
GITHUB_REPO = ""   # z.B. "deinname/FrediMailAssistent"
GITHUB_TOKEN = ""  # read-only PAT

# ─────────────────────────────────────────────────────────────────────────────

def _current_version():
    try:
        with open(VERSION_FILE, 'r') as f:
            return f.read().strip()
    except Exception:
        return '0.0.0'


def _check_and_update():
    if not GITHUB_REPO or not GITHUB_TOKEN:
        return
    try:
        import requests
        headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        url = f'https://raw.githubusercontent.com/{GITHUB_REPO}/main/version.txt'
        r = requests.get(url, headers=headers, timeout=6)
        if r.status_code != 200:
            return
        remote = r.text.strip()
        if remote == _current_version():
            return

        print(f'Update verfügbar: {remote} — wird heruntergeladen…')
        api_url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/app'
        r2 = requests.get(api_url, headers=headers, timeout=10)
        if r2.status_code != 200:
            return
        for fi in r2.json():
            if fi.get('type') == 'file' and fi['name'].endswith('.py'):
                content = requests.get(fi['download_url'], headers=headers, timeout=10)
                if content.status_code == 200:
                    with open(os.path.join(APP_DIR, fi['name']), 'w', encoding='utf-8') as f:
                        f.write(content.text)
        with open(VERSION_FILE, 'w') as f:
            f.write(remote)
        print('Update erfolgreich!')
    except Exception as e:
        print(f'Update-Prüfung fehlgeschlagen (wird ignoriert): {e}')


def _open_browser():
    # Poll until Flask responds, then open the browser — reliable on slow machines
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

    print('Prüfe auf Updates…')
    _check_and_update()

    print('Starte Server auf http://localhost:5000 …')
    threading.Thread(target=_open_browser, daemon=True).start()

    sys.path.insert(0, APP_DIR)
    from main import app
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)


if __name__ == '__main__':
    main()
