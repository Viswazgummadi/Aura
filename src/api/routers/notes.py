# src/api/routers/notes.py

from fastapi import APIRouter, Depends, HTTPException, status
from src.database.models import NoteCreate, NoteResponse, NoteUpdate, User, TagCreate
from src.api.dependencies import get_current_user
from src.agent.tools import notes as notes_tools

router = APIRouter(prefix="/notes", tags=["Notes"])
router_tags = APIRouter(prefix="/tags", tags=["Tags"])

@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_new_note(note: NoteCreate, current_user: User = Depends(get_current_user)):
    return notes_tools.create_note.invoke({
        "user_id": current_user.id, "title": note.title, "content": note.content
    })

@router.get("", response_model=list[NoteResponse])
def list_all_user_notes(current_user: User = Depends(get_current_user)):
    return notes_tools.get_all_notes.invoke({"user_id": current_user.id})

@router.get("/search/", response_model=list[NoteResponse])
def search_user_notes(q: str, current_user: User = Depends(get_current_user)):
    if not q: return []
    return notes_tools.search_notes.invoke({"user_id": current_user.id, "query": q})

@router.put("/{note_id}", response_model=NoteResponse)
def update_existing_note(note_id: int, note_update: NoteUpdate, current_user: User = Depends(get_current_user)):
    tool_input = note_update.model_dump(exclude_unset=True)
    tool_input["user_id"] = current_user.id
    tool_input["note_id"] = note_id
    result = notes_tools.update_note.invoke(tool_input)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_a_note(note_id: int, current_user: User = Depends(get_current_user)):
    result = notes_tools.delete_note.invoke({"user_id": current_user.id, "note_id": note_id})
    if "Error" in result:
        raise HTTPException(status_code=404, detail=result)
    return

@router.post("/{note_id}/tags", response_model=NoteResponse)
def add_a_tag_to_a_note(note_id: int, tag: TagCreate, current_user: User = Depends(get_current_user)):
    result = notes_tools.add_tag_to_note.invoke({
        "user_id": current_user.id, "note_id": note_id, "tag_name": tag.name
    })
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.delete("/{note_id}/tags/{tag_id}", response_model=NoteResponse)
def remove_a_tag_from_a_note(note_id: int, tag_id: int, current_user: User = Depends(get_current_user)):
    result = notes_tools.remove_tag_from_note.invoke({
        "user_id": current_user.id, "note_id": note_id, "tag_id": tag_id
    })
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router_tags.get("/{tag_name}/notes", response_model=list[NoteResponse])
def get_notes_for_a_tag(tag_name: str, current_user: User = Depends(get_current_user)):
    return notes_tools.get_notes_by_tag.invoke({"user_id": current_user.id, "tag_name": tag_name})