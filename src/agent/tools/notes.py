# File: src/agent/tools/notes.py

import json
import os
from datetime import datetime

# Define the path for our notes JSON file
NOTES_FILE = "notes.json"

def _load_notes() -> dict:
    """Loads notes from the JSON file. Returns an empty dict if file doesn't exist."""
    if not os.path.exists(NOTES_FILE):
        return {}
    try:
        with open(NOTES_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def _save_notes(notes: dict):
    """Saves the dictionary of notes to the JSON file."""
    with open(NOTES_FILE, 'w') as f:
        json.dump(notes, f, indent=4)

def save_note(key: str, value: str) -> dict:
    """
    Saves a new note or overwrites an existing one.

    Args:
        key: The key to identify the note (e.g., "wifi password").
        value: The information to be stored.

    Returns:
        The newly created note dictionary.
    """
    notes = _load_notes()
    key = key.lower().strip() # Normalize the key for easier lookup
    
    note_data = {
        "value": value,
        "created_at": datetime.now().isoformat()
    }
    
    notes[key] = note_data
    _save_notes(notes)
    print(f"Note saved: '{key}' -> '{value}'")
    return {key: note_data}

def get_note(key: str) -> str | None:
    """
    Retrieves a note by its key.

    Args:
        key: The key of the note to retrieve.

    Returns:
        The value of the note, or None if not found.
    """
    notes = _load_notes()
    key = key.lower().strip()
    note_data = notes.get(key)
    
    if note_data:
        return note_data.get('value')
    return None

def list_notes() -> dict:
    """
    Lists all saved notes.

    Returns:
        A dictionary of all notes.
    """
    return _load_notes()

def delete_note(key: str) -> bool:
    """
    Deletes a note by its key.

    Args:
        key: The key of the note to delete.

    Returns:
        True if the note was deleted, False otherwise.
    """
    notes = _load_notes()
    key = key.lower().strip()
    
    if key in notes:
        del notes[key]
        _save_notes(notes)
        print(f"Note deleted: '{key}'")
        return True
    return False