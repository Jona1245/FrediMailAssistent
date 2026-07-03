import os
import anthropic
import google.generativeai as genai

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


def _build_prompts(source_text, customer_name, customer_email, config):
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
    return system, user_msg


def _parse_response(text):
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
    return {'subject': subject, 'body': body}


_OPENROUTER_MODELS = [
    'qwen/qwen3-next-80b-a3b-instruct:free',   # ~3B active, sehr schnell
    'google/gemma-4-31b-it:free',               # 31B, schnell
    'nvidia/nemotron-3-super-120b-a12b:free',   # ~12B active, mittel
    'meta-llama/llama-3.3-70b-instruct:free',   # 70B, langsamer aber top Qualität
    'openai/gpt-oss-120b:free',                 # Fallback
]


def _generate_openrouter(source_text, customer_name, customer_email, config):
    import requests as _req
    api_key = config.get('openrouter_api_key', '').strip()
    if not api_key:
        return None, 'no_openrouter_key'

    system, user_msg = _build_prompts(source_text, customer_name, customer_email, config)
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://github.com/Jona1245/FrediMailAssistent',
        'X-Title': 'FrediMailAssistent',
    }
    messages = []
    if system:
        messages.append({'role': 'system', 'content': system})
    messages.append({'role': 'user', 'content': user_msg})

    last_error = 'Alle Modelle fehlgeschlagen.'
    for model in _OPENROUTER_MODELS:
        try:
            resp = _req.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers=headers,
                json={'model': model, 'messages': messages, 'max_tokens': 1500},
                timeout=60,
            )
            if resp.status_code == 401:
                return None, 'openrouter_auth_failed'
            if resp.status_code not in (200,):
                last_error = f'{model}: HTTP {resp.status_code}'
                continue
            data = resp.json()
            choices = data.get('choices') or []
            if not choices:
                # OpenRouter may return an error object inside 200
                err_obj = data.get('error', {})
                last_error = f'{model}: {err_obj.get("message", "Kein Ergebnis")}'
                continue
            text = (choices[0].get('message') or {}).get('content', '').strip()
            if not text:
                last_error = f'{model}: Leere Antwort'
                continue
            return _parse_response(text), None
        except Exception as e:
            last_error = f'{model}: {str(e)[:150]}'
            continue

    return None, f'OpenRouter-Fehler: {last_error}'


def _generate_anthropic(source_text, customer_name, customer_email, config):
    api_key = config.get('claude_api_key', '').strip()
    if not api_key:
        return None, 'no_api_key'

    model = config.get('claude_model', 'claude-haiku-4-5-20251001')
    system, user_msg = _build_prompts(source_text, customer_name, customer_email, config)

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
        return _parse_response(resp.content[0].text.strip()), None
    except anthropic.AuthenticationError:
        return None, 'auth_failed'
    except anthropic.APIConnectionError:
        return None, 'connection_failed_ai'
    except Exception as e:
        return None, f'Claude-Fehler: {str(e)[:300]}'


def _generate_gemini(source_text, customer_name, customer_email, config):
    api_key = config.get('gemini_api_key', '').strip()
    if not api_key:
        return None, 'no_gemini_key'

    model_name = config.get('gemini_model', 'gemini-2.0-flash')
    system, user_msg = _build_prompts(source_text, customer_name, customer_email, config)

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system or None,
        )
        resp = model.generate_content(user_msg)
        return _parse_response(resp.text.strip()), None
    except Exception as e:
        msg = str(e).lower()
        if any(x in msg for x in ('api key', 'invalid', 'permission', 'unauthenticated', '401', '403')):
            return None, 'gemini_auth_failed'
        return None, f'Gemini-Fehler: {str(e)[:300]}'


def generate_email(source_text, customer_name, customer_email, config):
    provider = config.get('ai_provider', 'auto')
    claude_key = config.get('claude_api_key', '').strip()
    gemini_key = config.get('gemini_api_key', '').strip()
    openrouter_key = config.get('openrouter_api_key', '').strip()

    if provider == 'gemini':
        return _generate_gemini(source_text, customer_name, customer_email, config)
    if provider == 'anthropic':
        return _generate_anthropic(source_text, customer_name, customer_email, config)
    if provider == 'openrouter':
        return _generate_openrouter(source_text, customer_name, customer_email, config)
    # auto: OpenRouter → Gemini → Claude
    if openrouter_key:
        return _generate_openrouter(source_text, customer_name, customer_email, config)
    if gemini_key:
        return _generate_gemini(source_text, customer_name, customer_email, config)
    if claude_key:
        return _generate_anthropic(source_text, customer_name, customer_email, config)
    return None, 'no_api_key'


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
