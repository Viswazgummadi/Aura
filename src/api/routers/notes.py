from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from src.database import crud
from src.database.database import get_db
from src.database.models import NoteCreate, NoteResponse, User # <-- NEW IMPORT: User model
from src.api.dependencies import get_current_user # <-- NEW IMPORT: Our authentication dependency

router = APIRouter(
    prefix="/notes",
    tags=["Notes"]
)

# Endpoint to save (create or update) a note (now secured and user-specific)
@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def save_note(
    note: NoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # <-- NEW: Requires authentication
):
    """
    Save a new note or update an existing one for the authenticated user.
    """
    print(f"API: Received request to save note '{note.key}' for user ID: {current_user.id}")
    # Pass current_user.id to the CRUD function
    db_note = crud.create_or_update_note(db=db, key=note.key, value=note.value, user_id=current_user.id)
    return db_note

# Endpoint to get a specific note by key (now secured and user-specific)
@router.get("/{note_key}", response_model=NoteResponse)
def get_note_by_key(
    note_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # <-- NEW: Requires authentication
):
    """
    Retrieve a specific note by its key for the authenticated user.
    """
    print(f"API: Received request to get note '{note_key}' for user ID: {current_user.id}")
    # Pass current_user.id to the CRUD function
    db_note = crud.get_note_by_key(db=db, key=note_key, user_id=current_user.id)
    if not db_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with key '{note_key}' not found for user {current_user.id}." # More specific error
        )
    return db_note

# Endpoint to list all notes (now secured and user-specific)
@router.get("", response_model=List[NoteResponse])
def list_all_notes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # <-- NEW: Requires authentication
):
    """
    Retrieve a list of all saved notes for the authenticated user.
    """
    print(f"API: Received request to list all notes for user ID: {current_user.id}")
    # Pass current_user.id to the CRUD function
    notes = crud.get_all_notes(db, user_id=current_user.id)
    return notes

# Endpoint to delete a note by key (now secured and user-specific)
@router.delete("/{note_key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note_by_key(
    note_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # <-- NEW: Requires authentication
):
    """
    Delete a specific note by its key for the authenticated user.
    """
    print(f"API: Received request to delete note '{note_key}' for user ID: {current_user.id}")
    # Pass current_user.id to the CRUD function
    deleted = crud.delete_note_by_key(db=db, key=note_key, user_id=current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with key '{note_key}' not found for user {current_user.id}." # More specific error
        )
    return