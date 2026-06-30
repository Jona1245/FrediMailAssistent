import json
import os
import uuid

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTACTS_FILE = os.path.join(_BASE, 'contacts.json')


def load_contacts():
    if not os.path.exists(CONTACTS_FILE):
        return []
    try:
        with open(CONTACTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def save_contacts(contacts):
    with open(CONTACTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(contacts, f, ensure_ascii=False, indent=2)


def add_contact(name, email):
    contacts = load_contacts()
    existing = next((c for c in contacts if c['email'].lower() == email.lower()), None)
    if existing:
        return existing
    contact = {'id': str(uuid.uuid4()), 'name': name, 'email': email}
    contacts.append(contact)
    save_contacts(contacts)
    return contact


def delete_contact(contact_id):
    contacts = load_contacts()
    contacts = [c for c in contacts if c['id'] != contact_id]
    save_contacts(contacts)


def find_or_create(name, email):
    contacts = load_contacts()
    for c in contacts:
        if c['email'].lower() == email.lower():
            return c
    return add_contact(name, email)
