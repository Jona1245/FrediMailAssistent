import json
import os
from cryptography.fernet import Fernet

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(_BASE, 'config.json')
KEY_FILE = os.path.join(_BASE, 'config.key')

ENCRYPTED_FIELDS = {'imap1_password', 'imap2_password', 'claude_api_key', 'gemini_api_key'}

DEFAULT_CONFIG = {
    'imap1_host': 'outlook.office365.com',
    'imap1_port': 993,
    'imap1_email': '',
    'imap1_password': '',
    'imap2_host': 'imap.mxhichina.com',
    'imap2_port': 993,
    'smtp2_host': 'smtp.mxhichina.com',
    'smtp2_port': 465,
    'smtp2_type': 'ssl',
    'imap2_email': '',
    'imap2_password': '',
    'claude_api_key': '',
    'claude_model': 'claude-haiku-4-5-20251001',
    'gemini_api_key': '',
    'gemini_model': 'gemini-2.0-flash',
    'ai_provider': 'auto',
    'system_prompt': (
        'Du bist der E-Mail-Assistent von Fredi Hartlaub, Geschäftsführer von SunProPower. '
        'Schreibe E-Mails in seinem Stil: professionell aber persönlich, klar strukturiert, auf Deutsch. '
        'Verwende NUR die freigegebenen Informationen aus der Eingangs-E-Mail. '
        'Beginne die E-Mail mit einer freundlichen Anrede und schließe mit freundlichen Grüßen.'
    ),
    'filter_rules': 'Interne Einkaufspreise\nLieferantennamen\nInterne Bestellnummern\nMargen und Kalkulationen',
    'theme': 'dark',
}


def _get_or_create_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, 'rb') as f:
            return f.read()
    key = Fernet.generate_key()
    with open(KEY_FILE, 'wb') as f:
        f.write(key)
    return key


def _fernet():
    return Fernet(_get_or_create_key())


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        fn = _fernet()
        config = DEFAULT_CONFIG.copy()
        for key, value in data.items():
            if key in ENCRYPTED_FIELDS and value:
                try:
                    config[key] = fn.decrypt(value.encode()).decode()
                except Exception:
                    config[key] = ''
            else:
                config[key] = value
        return config
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(config):
    fn = _fernet()
    data = {}
    for key, value in config.items():
        if key in ENCRYPTED_FIELDS and value:
            data[key] = fn.encrypt(str(value).encode()).decode()
        else:
            data[key] = value
    with open(CONFIG_FILE, 'w', encoding='utf-8') as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)
