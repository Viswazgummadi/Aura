# src/api/routers/admin.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from src.api.dependencies import get_current_admin_user
from src.database import crud, models
from src.database.database import get_db
from src.core.model_manager import llm_manager
from pydantic import BaseModel
class ActiveModelStatus(BaseModel):
    status: str
    active_model: str
    provider: str

class GenerationTestRequest(BaseModel):
    prompt: str = "Hello, world!"

class GenerationTestResponse(BaseModel):
    status: str
    prompt: str
    response: str
    
router = APIRouter(
    prefix="/admin",
    tags=["Admin - Model Management"],
    dependencies=[Depends(get_current_admin_user)]
)
# --- Provider Endpoints ---
@router.post("/providers", response_model=models.LLMProviderResponse)
def create_provider(provider: models.LLMProviderCreate, db: Session = Depends(get_db)):
    """Create a new LLM provider (e.g., 'google', 'openai')."""
    return crud.get_or_create_provider(db, provider_name=provider.name)

# --- API Key Endpoints ---
@router.post("/providers/{provider_name}/keys", response_model=models.APIKeyResponse)
def add_key_to_provider(provider_name: str, key: models.APIKeyCreate, db: Session = Depends(get_db)):
    """Add a new API key for a specific provider."""
    return crud.add_api_key(db, provider_name=provider_name, key=key.key)

@router.put("/keys/{key_id}/deactivate", response_model=models.APIKeyResponse)
def deactivate_key(key_id: int, db: Session = Depends(get_db)):
    """Deactivate an API key if it's compromised or rate-limited."""
    db_key = crud.deactivate_api_key(db, key_id=key_id)
    if not db_key:
        raise HTTPException(status_code=404, detail="API Key not found")
    return db_key

# --- Model Endpoints ---
@router.post("/providers/{provider_name}/models", response_model=models.LLMModelResponse)
def add_model_to_provider(provider_name: str, model: models.LLMModelCreate, db: Session = Depends(get_db)):
    """Add a new LLM model for a specific provider."""
    return crud.add_llm_model(db, provider_name=provider_name, model_name=model.name)

@router.put("/models/{model_name}/activate", response_model=models.LLMModelResponse)
def set_active_model(model_name: str, db: Session = Depends(get_db)):
    """
    Set a model as the active default for the agent.
    This will automatically deactivate any other active model.
    """
    db_model = crud.set_active_llm_model(db, model_name=model_name)
    if not db_model:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
    return db_model

@router.get("/models/status", response_model=ActiveModelStatus)
def get_active_model_status(db: Session = Depends(get_db)):
    """
    Health check to verify the ModelManager can identify the active model
    from the database.
    """
    try:
        # We don't need the model instance itself, just its configuration
        active_model_config = crud.get_active_llm_model(db)
        if not active_model_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active LLM model is configured in the database."
            )
        
        return ActiveModelStatus(
            status="ok",
            active_model=active_model_config.name,
            provider=active_model_config.provider.name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@router.post("/models/test-generation", response_model=GenerationTestResponse)
def test_model_generation(request: GenerationTestRequest, db: Session = Depends(get_db)):
    """
    Performs a live generation test with the currently active model.
    This verifies the entire chain: DB config -> API key -> Model init -> LLM call.
    """
    try:
        # This will trigger the full logic: get config, get key, init model
        active_model = llm_manager.get_active_model()
        
        print(f"INFO: [Admin Test] Performing generation with prompt: '{request.prompt}'")
        
        # Invoke the model to get a response
        response = active_model.invoke(request.prompt)
        
        return GenerationTestResponse(
            status="ok",
            prompt=request.prompt,
            response=response.content # .content holds the string response
        )
    except Exception as e:
        # This will catch errors like "No active model", "No API keys", or actual API errors from Google
        print(f"ERROR: [Admin Test] Generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to generate response: {str(e)}"
        )
        
@router.put("/users/{user_id}/promote", response_model=models.UserResponse)
def promote_user_to_admin(user_id: int, db: Session = Depends(get_db)):
    """
    Promotes a user to be an administrator.
    This endpoint can only be accessed by another administrator.
    """
    db_user = crud.set_user_admin_status(db, user_id=user_id, is_admin=True)
    if not db_user:
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")
    return db_user