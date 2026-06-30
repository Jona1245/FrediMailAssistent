import ssl
import os
import json as _json
import email
import smtplib
import tempfile
from email.header import decode_header as _decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import imapclient
import imapclient.exceptions

# Disk-based attachment cache — persists across Flask restarts
_CACHE_DIR = os.path.join(tempfile.gettempdir(), 'fredi_mail_atts')


def _cache_write(att_id, filename, content_type, data):
    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        with open(os.path.join(_CACHE_DIR, att_id + '.bin'), 'wb') as f:
            f.write(data)
        with open(os.path.join(_CACHE_DIR, att_id + '.json'), 'w', encoding='utf-8') as f:
            _json.dump({'filename': filename, 'content_type': content_type}, f)
    except Exception:
        pass


def _cache_read(att_id):
    json_path = os.path.join(_CACHE_DIR, att_id + '.json')
    bin_path  = os.path.join(_CACHE_DIR, att_id + '.bin')
    if not os.path.exists(json_path):
        return None
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            meta = _json.load(f)
        with open(bin_path, 'rb') as f:
            meta['data'] = f.read()
        return meta
    except Exception:
        return None


# ── helpers ──────────────────────────────────────────────────────────────────

def _decode_str(value):
    if value is None:
        return ''
    if isinstance(value, bytes):
        try:
            raw = value.decode('utf-8')
        except Exception:
            raw = value.decode('latin-1', errors='replace')
    else:
        raw = str(value)
    parts = _decode_header(raw)
    out = []
    for part, charset in parts:
        if isinstance(part, bytes):
            out.append(part.decode(charset or 'utf-8', errors='replace'))
        else:
            out.append(part)
    return ''.join(out)


def _imap_client(host, port):
    ctx = ssl.create_default_context()
    return imapclient.IMAPClient(host, port=int(port), ssl=True,
                                 ssl_context=ctx, use_uid=True, timeout=15)


# ── connections ───────────────────────────────────────────────────────────────

def connect_imap1(config):
    try:
        client = _imap_client(config['imap1_host'], config['imap1_port'])
        client.login(config['imap1_email'], config['imap1_password'])
        return client, None
    except imapclient.exceptions.LoginError as e:
        msg = str(e)
        if any(x in msg for x in ('AUTHENTICATIONFAILED', '535', 'credentials')):
            return None, 'auth_blocked'
        return None, 'login_failed'
    except Exception:
        return None, 'connection_failed'


def connect_imap2(config):
    try:
        client = _imap_client(config['imap2_host'], config['imap2_port'])
        client.login(config['imap2_email'], config['imap2_password'])
        return client, None
    except imapclient.exceptions.LoginError as e:
        msg = str(e)
        if any(x in msg for x in ('AUTHENTICATIONFAILED', '535', 'credentials')):
            return None, 'auth_blocked'
        return None, 'login_failed'
    except Exception:
        return None, 'connection_failed'


# ── public API ────────────────────────────────────────────────────────────────

def test_imap1(config):
    client, err = connect_imap1(config)
    if err:
        return err
    try:
        client.logout()
    except Exception:
        pass
    return None


def test_imap2(config):
    client, err = connect_imap2(config)
    if err:
        return err
    try:
        client.logout()
    except Exception:
        pass
    return None


def get_unread_emails(config, limit=60):
    client, err = connect_imap1(config)
    if err:
        return None, err
    try:
        client.select_folder('INBOX', readonly=True)

        # Always include every UNSEEN email, then fill with recent ALL up to limit.
        # This guarantees unread messages are visible even in a large mailbox.
        unseen_uids = set(client.search(['UNSEEN']))
        recent_uids = sorted(client.search(['ALL']), reverse=True)[:limit]
        cap = max(limit, min(len(unseen_uids), 100))
        combined = sorted(set(recent_uids) | unseen_uids, reverse=True)[:cap]

        if not combined:
            client.logout()
            return [], None

        raw = client.fetch(combined, ['ENVELOPE', 'FLAGS'])
        emails = []
        for uid, data in raw.items():
            env = data.get(b'ENVELOPE')
            flags = data.get(b'FLAGS', [])
            if env is None:
                continue
            unread = b'\\Seen' not in flags
            date_str = ''
            if env.date:
                try:
                    date_str = env.date.strftime('%d.%m.%Y %H:%M')
                except Exception:
                    date_str = str(env.date)
            emails.append({
                'uid': uid,
                'sender_name': _decode_str(env.from_[0].name) if env.from_ else '',
                'sender_email': (
                    f"{_decode_str(env.from_[0].mailbox)}@{_decode_str(env.from_[0].host)}"
                    if env.from_ else ''
                ),
                'subject': _decode_str(env.subject) or '(Kein Betreff)',
                'date': date_str,
                'unread': unread,
            })
        client.logout()
        return emails, None
    except Exception:
        try:
            client.logout()
        except Exception:
            pass
        return None, 'fetch_failed'


def get_email_content(config, uid):
    client, err = connect_imap1(config)
    if err:
        return None, err
    try:
        client.select_folder('INBOX', readonly=True)
        raw = client.fetch([uid], ['RFC822'])
        if uid not in raw:
            client.logout()
            return None, 'not_found'

        msg = email.message_from_bytes(raw[uid][b'RFC822'])
        body_text = ''
        body_html = ''
        attachments = []

        def _process_part(part):
            nonlocal body_text, body_html
            ct = part.get_content_type()
            cd = str(part.get('Content-Disposition', ''))
            if 'attachment' in cd or part.get_filename():
                filename = _decode_str(part.get_filename() or 'Anhang')
                payload = part.get_payload(decode=True) or b''
                att_id = f'{uid}_{len(attachments)}'
                _cache_write(att_id, filename, ct or 'application/octet-stream', payload)
                attachments.append({
                    'id': att_id,
                    'filename': filename,
                    'content_type': ct,
                    'size': len(payload),
                    'is_pdf': ct == 'application/pdf' or filename.lower().endswith('.pdf'),
                })
            elif ct == 'text/plain' and not body_text:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    body_text = payload.decode(charset, errors='replace')
            elif ct == 'text/html' and not body_html:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    body_html = payload.decode(charset, errors='replace')

        if msg.is_multipart():
            for part in msg.walk():
                if part.is_multipart():
                    continue
                _process_part(part)
        else:
            _process_part(msg)

        client.logout()
        return {
            'uid': uid,
            'subject': _decode_str(msg.get('Subject', '')) or '(Kein Betreff)',
            'from': _decode_str(msg.get('From', '')),
            'to': _decode_str(msg.get('To', '')),
            'date': msg.get('Date', ''),
            'body_text': body_text,
            'body_html': body_html,
            'attachments': attachments,
        }, None
    except Exception:
        try:
            client.logout()
        except Exception:
            pass
        return None, 'fetch_failed'


def get_attachment(att_id):
    return _cache_read(att_id)


def mark_as_read(config, uid):
    client, err = connect_imap1(config)
    if err:
        return err
    try:
        client.select_folder('INBOX')
        client.set_flags([uid], [b'\\Seen'])
        client.logout()
        return None
    except Exception:
        try:
            client.logout()
        except Exception:
            pass
        return 'mark_failed'


def send_email(config, to_name, to_email, subject, body,
               attachment_ids=None, local_files=None):
    try:
        msg = MIMEMultipart()
        msg['From'] = config['imap2_email']
        msg['To'] = f'{to_name} <{to_email}>' if to_name else to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        for att_id in (attachment_ids or []):
            att = _cache_read(att_id)
            if att:
                ct = att.get('content_type', 'application/octet-stream')
                main_type, _, sub_type = ct.partition('/')
                part = MIMEBase(main_type or 'application', sub_type or 'octet-stream')
                part.set_payload(att['data'])
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment',
                                filename=att['filename'])
                msg.attach(part)

        for fi in (local_files or []):
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(fi['data'])
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment',
                            filename=fi['filename'])
            msg.attach(part)

        ctx = ssl.create_default_context()
        smtp_type = config.get('smtp2_type', 'ssl')
        if smtp_type == 'starttls':
            with smtplib.SMTP(config['smtp2_host'], int(config['smtp2_port'])) as srv:
                srv.starttls(context=ctx)
                srv.login(config['imap2_email'], config['imap2_password'])
                srv.sendmail(config['imap2_email'], to_email, msg.as_bytes())
        else:
            with smtplib.SMTP_SSL(config['smtp2_host'],
                                  int(config['smtp2_port']), context=ctx) as srv:
                srv.login(config['imap2_email'], config['imap2_password'])
                srv.sendmail(config['imap2_email'], to_email, msg.as_bytes())
        return None
    except smtplib.SMTPAuthenticationError:
        return 'smtp_auth_failed'
    except smtplib.SMTPException:
        return 'smtp_failed'
    except Exception:
        return 'send_failed'
