# File: gmail_history_tracker.py

import json
import os

HISTORY_FILE = "gmail_history.json"

def _load_data() -> dict:
    if not os.path.exists(HISTORY_FILE):
        return {
            'last_history_id': None,
            'email_address': None,
            'processed_message_ids': []
        }
    try:
        with open(HISTORY_FILE, 'r') as f:
            data = json.load(f)
            data.setdefault('processed_message_ids', [])
            if isinstance(data['processed_message_ids'], list):
                data['processed_message_ids'] = list(set(data['processed_message_ids']))[-5000:]
            else:
                data['processed_message_ids'] = list(data['processed_message_ids'])
            return data
    except (json.JSONDecodeError, FileNotFoundError):
        return {
            'last_history_id': None,
            'email_address': None,
            'processed_message_ids': []
        }

def _save_data(data: dict):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_last_history_id() -> int | None:
    return _load_data().get('last_history_id')

def set_last_history_id(history_id: int):
    data = _load_data()
    data['last_history_id'] = history_id
    _save_data(data)

def get_current_email_address() -> str | None:
    return _load_data().get('email_address')

def set_current_email_address(email_address: str):
    data = _load_data()
    data['email_address'] = email_address
    _save_data(data)

def add_processed_message_id(message_id: str):
    data = _load_data()
    processed_ids_set = set(data['processed_message_ids'])
    if message_id not in processed_ids_set:
        processed_ids_set.add(message_id)
        data['processed_message_ids'] = list(processed_ids_set)[-5000:]
        _save_data(data)

def is_message_processed(message_id: str) -> bool:
    return message_id in set(_load_data().get('processed_message_ids', []))