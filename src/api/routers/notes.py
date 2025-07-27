# src/api/routers/notes.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from src.database import crud
from src.database.database import get_db
from src.database.models import NoteCreate, NoteResponse, NoteUpdate, User,TagCreate
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
    Create a new note for the authenticated user with a title and optional content.
    """
    return crud.create_note(db=db, note=note, user_id=current_user.id)

@router.get("", response_model=List[NoteResponse])
def list_all_user_notes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve a list of all saved notes for the authenticated user,
    ordered by the most recently updated.
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
    Update a note's title or content. Only the fields you provide
    in the request body will be updated.
    """
    updated_note = crud.update_note(db=db, note_id=note_id, note_update=note_update, user_id=current_user.id)
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
    # On successful deletion, we return a 204 status code with no content.
    return
# --- Add these new endpoints to the end of src/api/routers/notes.py ---

@router.post("/{note_id}/tags", response_model=NoteResponse)
def add_a_tag_to_a_note(
    note_id: int,
    tag: TagCreate, # We expect a small JSON like {"name": "work"}
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a tag to a specific note. If the tag doesn't exist, it will be
    created automatically.
    """
    updated_note = crud.add_tag_to_note(db, note_id=note_id, tag_name=tag.name, user_id=current_user.id)
    if not updated_note:
        raise HTTPException(status_code=404, detail="Note not found")
    return updated_note

@router.delete("/{note_id}/tags/{tag_id}", response_model=NoteResponse)
def remove_a_tag_from_a_note(
    note_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove a tag from a specific note.
    """
    updated_note = crud.remove_tag_from_note(db, note_id=note_id, tag_id=tag_id, user_id=current_user.id)
    if not updated_note:
        raise HTTPException(status_code=404, detail="Note or Tag association not found")
    return updated_note

# We are adding a new top-level router for tags to keep the API clean
router_tags = APIRouter(
    prefix="/tags",
    tags=["Tags"] # This will create a new section in your API docs
)

@router_tags.get("/{tag_name}/notes", response_model=List[NoteResponse])
def get_notes_for_a_tag(
    tag_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all notes for the authenticated user that are labeled
    with a specific tag.
    """
    return crud.get_notes_by_tag_name(db, tag_name=tag_name, user_id=current_user.id)

# Don't forget to import TagCreate at the top of the file!
# from src.database.models import ..., TagCreate, ...