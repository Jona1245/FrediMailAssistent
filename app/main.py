import os
import sys
import io
import re
import time as _time
import threading
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, jsonify, request, send_file, abort

from config_manager import load_config, save_config
from email_client import (
    get_unread_emails, get_email_content, get_attachment,
    get_sent_emails, get_sent_email_content,
    mark_as_read, mark_all_read, send_email, test_imap1, test_imap2,
)
from ai_generator import (
    generate_email, list_style_examples,
    save_style_example, delete_style_example,
)
from contacts import load_contacts, add_contact, delete_contact

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 25 MB upload limit

_BASE_DIR = os.environ.get('FREDI_BASE') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GITHUB_REPO = 'Jona1245/FrediMailAssistent'
_update_cache = {'ts': 0.0, 'info': None}


def _read_local_version():
    try:
        return open(os.path.join(_BASE_DIR, 'version.txt')).read().strip()
    except Exception:
        return '0.0.0'


def _fetch_update_info():
    """Check GitHub Releases API; result cached for 30 min."""
    now = _time.time()
    if now - _update_cache['ts'] < 1800:
        return _update_cache['info']
    info = None
    try:
        import requests
        r = requests.get(
            f'https://api.github.com/repos/{_GITHUB_REPO}/releases/latest',
            timeout=5,
            headers={'User-Agent': 'FrediMailAssistent/1.0'},
        )
        if r.status_code == 200:
            data = r.json()
            tag = data.get('tag_name', '')
            remote_ver = tag.lstrip('v')
            if remote_ver and remote_ver != _read_local_version():
                info = {'version': remote_ver, 'tag': tag, 'url': data.get('html_url', '')}
    except Exception:
        pass
    _update_cache['ts'] = now
    _update_cache['info'] = info
    return info


def _do_download_and_extract(tag):
    import requests, zipfile, shutil, tempfile
    zip_url = f'https://github.com/{_GITHUB_REPO}/archive/refs/tags/{tag}.zip'
    r = requests.get(zip_url, timeout=120, stream=True, headers={'User-Agent': 'FrediMailAssistent/1.0'})
    r.raise_for_status()

    tmp_zip = os.path.join(tempfile.gettempdir(), 'fredi_update.zip')
    with open(tmp_zip, 'wb') as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)

    _PRESERVE = {'python_embed', 'venv', 'config.json', 'config.key',
                 'contacts.json', 'style_examples', '__pycache__'}
    try:
        with tempfile.TemporaryDirectory() as extract_dir:
            with zipfile.ZipFile(tmp_zip) as zf:
                zf.extractall(extract_dir)
            entries = os.listdir(extract_dir)
            if not entries:
                raise RuntimeError('Leeres ZIP-Archiv.')
            inner = os.path.join(extract_dir, entries[0])
            for item in os.listdir(inner):
                if item in _PRESERVE:
                    continue
                src = os.path.join(inner, item)
                dst = os.path.join(_BASE_DIR, item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
    finally:
        try:
            os.unlink(tmp_zip)
        except Exception:
            pass

_ERRORS = {
    'login_failed': 'Anmeldung fehlgeschlagen. Bitte Zugangsdaten in den Einstellungen prüfen.',
    'connection_failed': 'Verbindung fehlgeschlagen. Bitte Internetverbindung und Server-Einstellungen prüfen.',
    'fetch_failed': 'E-Mails konnten nicht geladen werden. Bitte erneut versuchen.',
    'not_found': 'E-Mail nicht gefunden.',
    'mark_failed': 'E-Mail konnte nicht als gelesen markiert werden.',
    'smtp_auth_failed': 'Anmeldung bei Postfach 2 fehlgeschlagen. Zugangsdaten in den Einstellungen prüfen.',
    'smtp_failed': 'E-Mail konnte nicht gesendet werden. Bitte erneut versuchen.',
    'send_failed': 'E-Mail konnte nicht gesendet werden. Internetverbindung prüfen.',
    'no_api_key': 'Kein API-Key eingetragen. Bitte einen Key in den Einstellungen hinterlegen.',
    'no_gemini_key': 'Kein Gemini API-Key eingetragen. Bitte in den Einstellungen hinterlegen.',
    'no_openrouter_key': 'Kein OpenRouter API-Key eingetragen. Bitte in den Einstellungen hinterlegen.',
    'auth_failed': 'Claude API-Key ungültig. Bitte unter console.anthropic.com prüfen.',
    'gemini_auth_failed': 'Gemini API-Key ungültig. Bitte unter aistudio.google.com/apikey prüfen.',
    'openrouter_auth_failed': 'OpenRouter API-Key ungültig. Bitte unter openrouter.ai/keys prüfen.',
    'connection_failed_ai': 'KI nicht erreichbar. Bitte Internetverbindung prüfen.',
    'api_error': 'KI-Generierung fehlgeschlagen. Bitte erneut versuchen.',
}

MASKED = '••••••••'
SECRET_FIELDS = ('imap1_password', 'imap2_password', 'claude_api_key', 'gemini_api_key', 'openrouter_api_key')

_ALLOWED_CONFIG_KEYS = {
    'imap1_host', 'imap1_port', 'imap1_email', 'imap1_password',
    'imap2_host', 'imap2_port', 'smtp2_host', 'smtp2_port', 'smtp2_type',
    'imap2_email', 'imap2_password',
    'claude_api_key', 'claude_model',
    'gemini_api_key', 'gemini_model',
    'openrouter_api_key', 'ai_provider',
    'system_prompt', 'filter_rules', 'theme',
}


def _provider_hint(host):
    h = (host or '').lower()
    if 'office365' in h or 'outlook' in h:
        return ('Microsoft blockiert die Anmeldung. Bitte ein App-Passwort erstellen: '
                'https://account.microsoft.com/security → "App-Kennwörter".')
    if 'gmail' in h:
        return ('Google blockiert die Anmeldung. Bitte ein App-Passwort erstellen '
                '(2-Faktor-Auth muss aktiv sein): https://myaccount.google.com/apppasswords')
    if 'mailfence' in h:
        return ('Anmeldung fehlgeschlagen. Bitte E-Mail-Adresse und Passwort prüfen. '
                'Bei Mailfence ist kein App-Passwort nötig — das normale Passwort verwenden.')
    if 'mail.com' in h:
        return ('Anmeldung fehlgeschlagen. Bitte Passwort prüfen. Falls IMAP noch nicht aktiviert: '
                'In mail.com-Einstellungen → POP3 & IMAP → einschalten.')
    if 'web.de' in h or 'gmx' in h:
        return ('Anmeldung fehlgeschlagen. Bei web.de/GMX muss der IMAP-Zugriff zuerst in den '
                'Webmail-Einstellungen freigeschaltet werden: Einstellungen → POP3/IMAP/Weiterleitung → '
                '"Zugriff per IMAP zulassen" aktivieren.')
    return 'Anmeldung fehlgeschlagen. Bitte Zugangsdaten in den Einstellungen prüfen.'


def err(code, host=None):
    if code == 'auth_blocked':
        return _provider_hint(host)
    return _ERRORS.get(code, 'Ein unbekannter Fehler ist aufgetreten. Bitte erneut versuchen.')


# ── pages ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    config = load_config()
    needs_setup = not config.get('imap1_email') or (not config.get('claude_api_key') and not config.get('gemini_api_key'))
    return render_template('index.html', needs_setup=needs_setup,
                           theme=config.get('theme', 'dark'))


@app.route('/settings')
def settings():
    config = load_config()
    safe = dict(config)
    for f in SECRET_FIELDS:
        if safe.get(f):
            safe[f] = MASKED
    return render_template('settings.html', config=safe,
                           theme=config.get('theme', 'dark'))


# ── emails ────────────────────────────────────────────────────────────────────

@app.route('/api/emails')
def api_emails():
    config = load_config()
    if not config.get('imap1_email') or not config.get('imap1_password'):
        return jsonify({'error': 'Postfach 1 nicht konfiguriert. Bitte Einstellungen öffnen.'})
    before_uid = request.args.get('before_uid', type=int)
    emails, error, has_more = get_unread_emails(config, before_uid=before_uid)
    if error:
        return jsonify({'error': err(error, config.get('imap1_host'))})
    return jsonify({'emails': emails, 'has_more': has_more})


@app.route('/api/email/<int:uid>')
def api_email(uid):
    config = load_config()
    content, error = get_email_content(config, uid)
    if error:
        return jsonify({'error': err(error, config.get('imap1_host'))})
    return jsonify(content)


@app.route('/api/attachment/<att_id>')
def api_attachment(att_id):
    if not re.match(r'^s?\d+_\d+$', att_id):
        abort(404)
    att = get_attachment(att_id)
    if not att:
        abort(404)
    return send_file(
        io.BytesIO(att['data']),
        mimetype=att['content_type'],
        as_attachment=False,
        download_name=att['filename'],
    )


@app.route('/api/sent-emails')
def api_sent_emails():
    config = load_config()
    if not config.get('imap2_email') or not config.get('imap2_password'):
        return jsonify({'error': 'Postfach 2 nicht konfiguriert.'})
    before_uid = request.args.get('before_uid', type=int)
    emails, error, has_more = get_sent_emails(config, before_uid=before_uid)
    if error:
        return jsonify({'error': err(error, config.get('imap2_host'))})
    return jsonify({'emails': emails, 'has_more': has_more})


@app.route('/api/sent-email/<int:uid>')
def api_sent_email(uid):
    config = load_config()
    content, error = get_sent_email_content(config, uid)
    if error:
        return jsonify({'error': err(error, config.get('imap2_host'))})
    return jsonify(content)


@app.route('/api/mark-all-read', methods=['POST'])
def api_mark_all_read():
    config = load_config()
    error, count = mark_all_read(config)
    if error:
        return jsonify({'error': err(error, config.get('imap1_host'))})
    return jsonify({'success': True, 'count': count})


@app.route('/api/mark-read', methods=['POST'])
def api_mark_read():
    uid = (request.json or {}).get('uid')
    config = load_config()
    error = mark_as_read(config, uid)
    if error:
        return jsonify({'error': err(error, config.get('imap1_host'))})
    return jsonify({'success': True})


# ── generate & send ───────────────────────────────────────────────────────────

@app.route('/api/generate', methods=['POST'])
def api_generate():
    data = request.json or {}
    source_text = data.get('source_text', '').strip()
    customer_name = data.get('customer_name', '').strip()
    customer_email = data.get('customer_email', '').strip()

    if not source_text:
        return jsonify({'error': 'Kein E-Mail-Text vorhanden.'})
    if not customer_email:
        return jsonify({'error': 'Bitte eine Kunden-E-Mail-Adresse angeben.'})

    config = load_config()
    result, error = generate_email(source_text, customer_name, customer_email, config)
    if error:
        return jsonify({'error': err(error) if error in _ERRORS else error})
    return jsonify(result)


@app.route('/api/send', methods=['POST'])
def api_send():
    config = load_config()
    if not config.get('imap2_email') or not config.get('imap2_password'):
        return jsonify({'error': 'Postfach 2 nicht konfiguriert. Bitte Einstellungen öffnen.'})

    to_name = request.form.get('to_name', '').strip()
    to_email = request.form.get('to_email', '').strip()
    subject = request.form.get('subject', '').strip()
    body = request.form.get('body', '').strip()
    attachment_ids = request.form.getlist('attachment_ids')
    cc = request.form.get('cc', '').strip()
    source_uid = request.form.get('source_uid')

    if not to_email:
        return jsonify({'error': 'Bitte eine Empfänger-E-Mail-Adresse angeben.'})
    if not subject:
        return jsonify({'error': 'Bitte einen Betreff eingeben.'})
    if not body:
        return jsonify({'error': 'Bitte einen E-Mail-Text eingeben.'})

    local_files = []
    for key in request.files:
        f = request.files[key]
        if f and f.filename:
            local_files.append({'filename': f.filename, 'data': f.read()})

    error = send_email(config, to_name, to_email, subject, body,
                       attachment_ids or None, local_files or None, cc or None)
    if error:
        return jsonify({'error': err(error)})

    if source_uid:
        try:
            mark_as_read(config, int(source_uid))
        except (ValueError, TypeError):
            pass

    return jsonify({'success': True})


# ── contacts ──────────────────────────────────────────────────────────────────

@app.route('/api/contacts')
def api_contacts():
    return jsonify(load_contacts())


@app.route('/api/contacts', methods=['POST'])
def api_add_contact():
    data = request.json or {}
    contact = add_contact(data.get('name', ''), data.get('email', ''))
    return jsonify(contact)


@app.route('/api/contacts/<contact_id>', methods=['DELETE'])
def api_delete_contact(contact_id):
    delete_contact(contact_id)
    return jsonify({'success': True})


# ── config ────────────────────────────────────────────────────────────────────

@app.route('/api/config')
def api_config():
    config = load_config()
    safe = dict(config)
    for f in SECRET_FIELDS:
        if safe.get(f):
            safe[f] = MASKED
    return jsonify(safe)


@app.route('/api/config', methods=['POST'])
def api_save_config():
    data = request.json or {}
    config = load_config()
    for key, value in data.items():
        if key not in _ALLOWED_CONFIG_KEYS:
            continue
        if value == MASKED:
            continue
        config[key] = value
    save_config(config)
    return jsonify({'success': True})


@app.route('/api/test-connection', methods=['POST'])
def api_test_connection():
    data = request.json or {}
    mailbox = data.get('mailbox', 1)
    config = load_config()

    prefix = 'imap1' if mailbox == 1 else 'imap2'
    for field in ('host', 'port', 'email'):
        val = str(data.get(field, '')).strip()
        if val:
            config[f'{prefix}_{field}'] = val

    test_pw = data.get('password', '')
    if test_pw and test_pw != MASKED:
        config[f'{prefix}_password'] = test_pw

    error = test_imap1(config) if mailbox == 1 else test_imap2(config)
    if error:
        host = config.get('imap1_host') if mailbox == 1 else config.get('imap2_host')
        return jsonify({'error': err(error, host)})
    return jsonify({'success': True})


# ── style examples ────────────────────────────────────────────────────────────

@app.route('/api/style-examples')
def api_style_examples():
    return jsonify(list_style_examples())


@app.route('/api/style-examples/upload', methods=['POST'])
def api_upload_style():
    if 'file' not in request.files:
        return jsonify({'error': 'Keine Datei ausgewählt.'})
    f = request.files['file']
    if not f.filename.endswith('.txt'):
        return jsonify({'error': 'Nur .txt-Dateien sind erlaubt.'})
    content = f.read().decode('utf-8', errors='replace')
    save_style_example(f.filename, content)
    return jsonify({'success': True})


@app.route('/api/style-examples/<filename>', methods=['DELETE'])
def api_delete_style(filename):
    delete_style_example(filename)
    return jsonify({'success': True})


# ── restart ───────────────────────────────────────────────────────────────────

@app.route('/api/restart', methods=['POST'])
def api_restart():
    def _do():
        _time.sleep(1)
        python_exe = os.environ.get('FREDI_PYTHON', sys.executable)
        launcher = os.environ.get('FREDI_LAUNCHER', os.path.join(_BASE_DIR, 'launcher.py'))
        subprocess.Popen([python_exe, launcher])
        os._exit(0)
    threading.Thread(target=_do, daemon=True).start()
    return jsonify({'success': True})


# ── update ────────────────────────────────────────────────────────────────────

@app.route('/api/update-status')
def api_update_status():
    info = _fetch_update_info()
    if info:
        return jsonify({'version': info['version'], 'url': info['url']})
    return jsonify({'version': None})


@app.route('/api/do-update', methods=['POST'])
def api_do_update():
    info = _fetch_update_info()
    if not info:
        return jsonify({'error': 'Kein Update verfügbar.'})
    try:
        _do_download_and_extract(info['tag'])
    except Exception as e:
        return jsonify({'error': str(e)})

    def _restart():
        _time.sleep(2)
        python_exe = os.environ.get('FREDI_PYTHON', sys.executable)
        launcher = os.environ.get('FREDI_LAUNCHER', os.path.join(_BASE_DIR, 'launcher.py'))
        subprocess.Popen([python_exe, launcher])
        os._exit(0)

    threading.Thread(target=_restart, daemon=True).start()
    return jsonify({'success': True})


# ── run ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
