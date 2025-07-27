# src/api/routers/agent.py

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel # <-- THIS IS THE FIX
from sqlalchemy.orm import Session
from typing import List
import uuid
import datetime
# We will need these later for the actual agent
# from langchain.schema import HumanMessage, AIMessage

from src.database import crud, models
from src.database.database import get_db
from src.api.dependencies import get_current_user
from src.agent.memory.manager import memory_manager
from src.agent.graph.builder import get_agent_graph
from langchain_core.messages import HumanMessage
from src.database.models import ChatMessageResponse
import datetime


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
    Manages session history and invokes the LangGraph agent.
    """
    # Use the request's session_id or generate a new one
    session_id = request.session_id or str(uuid.uuid4())
    
    # 1. Load the history for this session
    chat_history = memory_manager.get_chat_history(user_id=current_user.id, session_id=session_id)
    
    # 2. Get the agent graph (it will be built on the first request)
    agent_graph = get_agent_graph()
    
    # 3. Define the config for this run
    config = {"configurable": {"user_id": current_user.id}}
    
    # 4. Invoke the agent graph with the message and config
    response = agent_graph.invoke({
        "messages": chat_history.messages + [HumanMessage(content=request.message)]
    }, config=config)
    
    # The agent's final response is the last message in the output
    final_response_message = response['messages'][-1]
    
    # 5. Save the user's message and the agent's final response to history
    user_message_to_save = HumanMessage(content=request.message)
    memory_manager.add_chat_message(
        user_id=current_user.id,
        session_id=session_id,
        message=user_message_to_save
    )
    memory_manager.add_chat_message(
        user_id=current_user.id,
        session_id=session_id,
        message=final_response_message
    )

    # Return a properly formatted response
    return models.ChatMessageResponse(
        id=0, # This is a dummy ID as we don't need to return the DB id
        session_id=session_id,
        message=str(final_response_message.content),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )