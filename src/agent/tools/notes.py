# src/agent/tools/notes.py

from langchain_core.tools import tool
from typing import List, Dict
from src.database import crud, database, models

@tool
def create_note(user_id: int, title: str, content: str) -> Dict:
    """
    Creates a new note with a title and content for a specific user.
    Use this to save information, ideas, or summaries.
    Returns the created note as a dictionary.
    """
    db = database.SessionLocal()
    try:
        note_create = models.NoteCreate(title=title, content=content)
        db_note = crud.create_note(db, note=note_create, user_id=user_id)
        return models.NoteResponse.from_orm(db_note).model_dump()
    finally:
        db.close()

@tool
def get_all_notes(user_id: int) -> List[Dict]:
    """Retrieves a list of all notes for a specific user."""
    db = database.SessionLocal()
    try:
        notes = crud.get_all_notes(db, user_id=user_id)
        return [models.NoteResponse.from_orm(note).model_dump() for note in notes]
    finally:
        db.close()

@tool
def search_notes(user_id: int, query: str) -> List[Dict]:
    """
    Searches the notes of a specific user for a given query string.
    The search is case-insensitive and checks both the note titles and content.
    """
    db = database.SessionLocal()
    try:
        notes = crud.search_notes(db, query=query, user_id=user_id)
        return [models.NoteResponse.from_orm(note).model_dump() for note in notes]
    finally:
        db.close()

@tool
def update_note(user_id: int, note_id: int, title: str = None, content: str = None) -> Dict:
    """
    Updates a note's title or content. You must provide the note_id.
    Only include the fields you want to change.
    """
    db = database.SessionLocal()
    try:
        note_update = models.NoteUpdate(title=title, content=content)
        updated_note = crud.update_note(db, note_id=note_id, note_update=note_update, user_id=user_id)
        if not updated_note:
            return {"error": f"Note with ID {note_id} not found."}
        return models.NoteResponse.from_orm(updated_note).model_dump()
    finally:
        db.close()

@tool
def delete_note(user_id: int, note_id: int) -> Dict: # <-- Change return type hint to Dict
    """Deletes a note by its ID. Use this to permanently remove a note."""
    db = database.SessionLocal()
    try:
        deleted = crud.delete_note_by_id(db, note_id=note_id, user_id=user_id)
        if not deleted:
            # Standardized error format
            return {"error": f"Note with ID '{note_id}' not found."}
        # Structured success message
        return {"status": "success", "message": f"Note with ID '{note_id}' has been deleted."}
    finally:
        db.close()

@tool
def add_tag_to_note(user_id: int, note_id: int, tag_name: str) -> Dict:
    """Adds a tag to a specific note for a user. e.g., 'work' or 'urgent'."""
    db = database.SessionLocal()
    try:
        note = crud.add_tag_to_note(db, note_id=note_id, tag_name=tag_name, user_id=user_id)
        if not note:
            return {"error": "Note not found or could not add tag."}
        return models.NoteResponse.from_orm(note).model_dump()
    finally:
        db.close()

@tool
def remove_tag_from_note(user_id: int, note_id: int, tag_id: int) -> Dict:
    """Removes a tag from a specific note, using the note_id and the tag_id."""
    db = database.SessionLocal()
    try:
        note = crud.remove_tag_from_note(db, note_id=note_id, tag_id=tag_id, user_id=user_id)
        if not note:
            return {"error": "Note or Tag association not found."}
        return models.NoteResponse.from_orm(note).model_dump()
    finally:
        db.close()

@tool
def get_notes_by_tag(user_id: int, tag_name: str) -> List[Dict]:
    """Gets all notes for a user that are labeled with a specific tag."""
    db = database.SessionLocal()
    try:
        notes = crud.get_notes_by_tag_name(db, tag_name=tag_name, user_id=user_id)
        return [models.NoteResponse.from_orm(note).model_dump() for note in notes]
    finally:
        db.close()
@tool
def link_task_to_note(user_id: int, note_id: int, task_id: str) -> Dict:
    """
    Links an existing task to a note. Use this to associate an action item with a piece of reference material.
    You must provide both the note_id and the task_id.
    """
    db = database.SessionLocal()
    try:
        updated_note = crud.link_note_to_task(db, note_id=note_id, task_id=task_id, user_id=user_id)
        if not updated_note:
            return {"error": "Note or Task not found, or they do not both belong to the user."}
        return models.NoteResponse.from_orm(updated_note).model_dump()
    finally:
        db.close()

@tool
def unlink_task_from_note(user_id: int, note_id: int, task_id: str) -> Dict:
    """
    Removes the link between a task and a note. The note and task themselves are not deleted.
    You must provide both the note_id and the task_id.
    """
    db = database.SessionLocal()
    try:
        updated_note = crud.unlink_note_from_task(db, note_id=note_id, task_id=task_id, user_id=user_id)
        if not updated_note:
            return {"error": "Note or Task not found, or the link does not exist."}
        return models.NoteResponse.from_orm(updated_note).model_dump()
    finally:
        db.close()