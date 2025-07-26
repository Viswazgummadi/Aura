# Import the CRUD functions we want to use and the session management
from src.database import crud
from src.database.database import SessionLocal

# --- Public Tool Functions ---

def save_note(key: str, value: str) -> dict:
    """
    Saves a new note or overwrites an existing one to the database.

    Args:
        key: The key to identify the note (e.g., "wifi password").
        value: The information to be stored.

    Returns:
        A dictionary representing the newly created or updated note.
    """
    print(f"TOOL: save_note called with key: '{key}', value: '{value}'")
    db = SessionLocal()
    try:
        # Call the CRUD function to create or update the note in the database
        db_note = crud.create_or_update_note(db=db, key=key, value=value)
        
        # Return a dictionary representation of the note
        return {
            "key": db_note.key,
            "value": db_note.value,
            "created_at": db_note.created_at.isoformat(),
            "updated_at": db_note.updated_at.isoformat()
        }
    finally:
        db.close()

def get_note(key: str) -> str | None:
    """
    Retrieves a note by its key from the database.

    Args:
        key: The key of the note to retrieve.

    Returns:
        The value of the note (string), or None if not found.
    """
    print(f"TOOL: get_note called with key: '{key}'")
    db = SessionLocal()
    try:
        # Call the CRUD function to get the note by key
        db_note = crud.get_note_by_key(db=db, key=key)
        
        if db_note:
            return db_note.value
        return None
    finally:
        db.close()

def list_notes() -> list[dict]:
    """
    Lists all saved notes from the database.

    Returns:
        A list of dictionaries, each representing a note.
    """
    print("TOOL: list_notes called")
    db = SessionLocal()
    try:
        # Call the CRUD function to get all notes
        notes_from_db = crud.get_all_notes(db=db)
        
        # Convert the list of Note objects into a list of dictionaries
        return [
            {
                "key": note.key,
                "value": note.value,
                "created_at": note.created_at.isoformat(),
                "updated_at": note.updated_at.isoformat()
            }
            for note in notes_from_db
        ]
    finally:
        db.close()

def delete_note(key: str) -> bool:
    """
    Deletes a note by its key from the database.

    Args:
        key: The key of the note to delete.

    Returns:
        True if the note was deleted, False otherwise.
    """
    print(f"TOOL: delete_note called with key: '{key}'")
    db = SessionLocal()
    try:
        # Call the CRUD function to delete the note
        deleted = crud.delete_note_by_key(db=db, key=key)
        return deleted
    finally:
        db.close()