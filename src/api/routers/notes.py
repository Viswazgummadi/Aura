# src/api/routers/notes.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# All necessary model imports are here
from src.database.models import (
    NoteCreate, NoteResponse, NoteUpdate, User, TagCreate
)
from src.api.dependencies import get_current_user
# Import the tools module which is now our source of truth
from src.agent.tools import notes as notes_tools

# Main router for /notes endpoints
router = APIRouter(
    prefix="/notes",
    tags=["Notes"]
)

# Separate router for tag-specific endpoints for a cleaner API design
router_tags = APIRouter(
    prefix="/tags",
    tags=["Tags"]
)


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_new_note(note: NoteCreate, current_user: User = Depends(get_current_user)):
    return notes_tools.create_note(
        user_id=current_user.id, title=note.title, content=note.content
    )

@router.get("", response_model=List[NoteResponse])
def list_all_user_notes(current_user: User = Depends(get_current_user)):
    return notes_tools.get_all_notes(user_id=current_user.id)

@router.get("/search/", response_model=List[NoteResponse])
def search_user_notes(q: str, current_user: User = Depends(get_current_user)):
    if not q: return []
    return notes_tools.search_notes(user_id=current_user.id, query=q)

@router.put("/{note_id}", response_model=NoteResponse)
def update_existing_note(note_id: int, note_update: NoteUpdate, current_user: User = Depends(get_current_user)):
    result = notes_tools.update_note(
        user_id=current_user.id, note_id=note_id, title=note_update.title, content=note_update.content
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_a_note(note_id: int, current_user: User = Depends(get_current_user)):
    result = notes_tools.delete_note(user_id=current_user.id, note_id=note_id)
    if "Error" in result:
        raise HTTPException(status_code=404, detail=result)
    return

@router.post("/{note_id}/tags", response_model=NoteResponse)
def add_a_tag_to_a_note(note_id: int, tag: TagCreate, current_user: User = Depends(get_current_user)):
    result = notes_tools.add_tag_to_note(
        user_id=current_user.id, note_id=note_id, tag_name=tag.name
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.delete("/{note_id}/tags/{tag_id}", response_model=NoteResponse)
def remove_a_tag_from_a_note(note_id: int, tag_id: int, current_user: User = Depends(get_current_user)):
    result = notes_tools.remove_tag_from_note(
        user_id=current_user.id, note_id=note_id, tag_id=tag_id
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router_tags.get("/{tag_name}/notes", response_model=List[NoteResponse])
def get_notes_for_a_tag(tag_name: str, current_user: User = Depends(get_current_user)):
    return notes_tools.get_notes_by_tag(user_id=current_user.id, tag_name=tag_name)