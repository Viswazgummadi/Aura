# src/api/routers/admin.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from src.api.dependencies import get_current_admin_user
from src.database import crud, models
from src.database.database import get_db

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