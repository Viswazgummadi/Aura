# src/api/routers/notes.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from src.database import crud
from src.database.database import get_db
from src.database.models import NoteCreate, NoteResponse, NoteUpdate, User
from src.api.dependencies import get_current_user

router = APIRouter(
    prefix="/notes",
    tags=["Notes"]
)

@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_new_note(
    note: NoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new note for the authenticated user with a title and content.
    """
    return crud.create_note(db=db, note=note, user_id=current_user.id)

@router.get("", response_model=List[NoteResponse])
def list_all_user_notes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve a list of all saved notes for the authenticated user.
    """
    return crud.get_all_notes(db, user_id=current_user.id)

@router.get("/{note_id}", response_model=NoteResponse)
def get_single_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve a specific note by its unique ID.
    """
    db_note = crud.get_note_by_id(db=db, note_id=note_id, user_id=current_user.id)
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    return db_note

@router.put("/{note_id}", response_model=NoteResponse)
def update_existing_note(
    note_id: int,
    note_update: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a note's title or content.
    """
    updated_note = crud.update_note(db, note_id=note_id, note_update=note_update, user_id=current_user.id)
    if not updated_note:
        raise HTTPException(status_code=404, detail="Note not found")
    return updated_note

@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_a_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a specific note by its ID.
    """
    deleted = crud.delete_note_by_id(db=db, note_id=note_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found")
    return