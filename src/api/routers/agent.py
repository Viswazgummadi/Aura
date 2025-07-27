# src/api/routers/agent.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

# We will need these later for the actual agent
# from langchain.schema import HumanMessage, AIMessage

from src.database import crud, models
from src.database.database import get_db
from src.api.dependencies import get_current_user
from src.agent.memory.manager import memory_manager

router = APIRouter(
    prefix="/agent",
    tags=["Agent - Conversational AI"]
)

# --- Pydantic models for our chat endpoint ---
class ChatRequest(BaseModel):
    session_id: str # To keep track of the conversation
    message: str

class MemoryRequest(BaseModel):
    content: str

# --- Temporary Test Endpoints for Memory ---
# These endpoints allow us to directly test the MemoryManager before the full agent is built.

@router.post("/test/long_term_memory", status_code=status.HTTP_201_CREATED)
def add_to_long_term_memory_test(
    request: MemoryRequest,
    current_user: models.User = Depends(get_current_user)
):
    """
    (TESTING ONLY) Directly add a piece of content to the user's
    long-term semantic memory.
    """
    try:
        memory_manager.add_to_long_term_memory(user_id=current_user.id, content=request.content)
        return {"status": "success", "message": "Content added to long-term memory."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.get("/test/long_term_memory/search")
def search_long_term_memory_test(
    q: str,
    current_user: models.User = Depends(get_current_user)
):
    """
    (TESTING ONLY) Perform a semantic search on the user's
    long-term memory.
    """
    try:
        results = memory_manager.search_long_term_memory(user_id=current_user.id, query=q)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# --- The Future Agent Chat Endpoint (Placeholder) ---
# We will build the real logic for this in Phase 3. For now, it's a placeholder.
@router.post("/chat")
def chat_with_agent(
    request: ChatRequest,
    current_user: models.User = Depends(get_current_user)
):
    """
    The primary endpoint for conversing with the Aura agent.
    """
    # In Phase 3, this will invoke the LangGraph agent.
    # For now, we'll just echo the message back.
    return {
        "session_id": request.session_id,
        "response": f"Placeholder response to: '{request.message}'"
    }