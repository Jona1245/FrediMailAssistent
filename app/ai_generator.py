import os
import anthropic

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STYLE_DIR = os.path.join(_BASE, 'style_examples')


def _load_style_examples():
    if not os.path.exists(STYLE_DIR):
        os.makedirs(STYLE_DIR)
        return ''
    parts = []
    for fn in sorted(os.listdir(STYLE_DIR)):
        if fn.endswith('.txt'):
            try:
                with open(os.path.join(STYLE_DIR, fn), 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                if content:
                    parts.append(f'--- Beispiel ({fn}) ---\n{content}')
            except Exception:
                pass
    return '\n\n'.join(parts)


def generate_email(source_text, customer_name, customer_email, config):
    api_key = config.get('claude_api_key', '').strip()
    if not api_key:
        return None, 'no_api_key'

    model = config.get('claude_model', 'claude-haiku-4-5-20251001')
    system_prompt = config.get('system_prompt', '')
    filter_rules = config.get('filter_rules', '')
    style_examples = _load_style_examples()

    filter_section = ''
    if filter_rules:
        rules = [r.strip() for r in filter_rules.splitlines() if r.strip()]
        filter_section = (
            '\n\nFILTERREGELN — diese Informationen NIEMALS in Kunden-E-Mails erwähnen:\n'
            + '\n'.join(f'- {r}' for r in rules)
        )

    style_section = ''
    if style_examples:
        style_section = f'\n\nSTIL-BEISPIELE (schreibe in genau diesem Stil):\n{style_examples}'

    system = system_prompt + filter_section + style_section

    user_msg = (
        f'Erstelle eine fertige Kunden-E-Mail basierend auf dieser eingehenden E-Mail:\n\n'
        f'--- EINGEHENDE E-MAIL ---\n{source_text}\n--- ENDE ---\n\n'
        f'Empfänger: {customer_name} <{customer_email}>\n\n'
        f'Antworte AUSSCHLIESSLICH mit:\n'
        f'Betreff: <Betreff hier>\n\n'
        f'<E-Mail-Text hier>\n\n'
        f'Kein erklärender Text, nur die fertige E-Mail.'
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=model,
            max_tokens=1500,
            system=system,
            messages=[{'role': 'user', 'content': user_msg}],
        )
        if not resp.content:
            return None, 'api_error'
        text = resp.content[0].text.strip()

        subject = ''
        body_lines = []
        in_body = False
        for line in text.splitlines():
            if not in_body and line.lower().startswith('betreff:'):
                subject = line[len('betreff:'):].strip()
            elif subject and not in_body and line.strip() == '':
                in_body = True
            elif in_body:
                body_lines.append(line)

        body = '\n'.join(body_lines).strip()
        if not subject:
            subject = 'Ihre Anfrage – SunProPower'
        if not body:
            body = text

        return {'subject': subject, 'body': body}, None

    except anthropic.AuthenticationError:
        return None, 'auth_failed'
    except anthropic.APIConnectionError:
        return None, 'connection_failed_ai'
    except Exception:
        return None, 'api_error'


def list_style_examples():
    if not os.path.exists(STYLE_DIR):
        os.makedirs(STYLE_DIR)
    return sorted(f for f in os.listdir(STYLE_DIR) if f.endswith('.txt'))


def save_style_example(filename, content):
    if not os.path.exists(STYLE_DIR):
        os.makedirs(STYLE_DIR)
    safe = os.path.basename(filename)
    if not safe.endswith('.txt'):
        safe += '.txt'
    with open(os.path.join(STYLE_DIR, safe), 'w', encoding='utf-8') as f:
        f.write(content)


def delete_style_example(filename):
    safe = os.path.basename(filename)
    path = os.path.join(STYLE_DIR, safe)
    if os.path.exists(path):
        os.remove(path)
