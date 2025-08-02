# File: src/api/routers/settings.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# Import all the necessary dependencies and database models/schemas
from src.api.dependencies import get_current_user
from src.database import crud, models, database

# All endpoints in this router will require a logged-in user.
router = APIRouter(
    prefix="/settings",
    tags=["User - Agent Settings"],
    dependencies=[Depends(get_current_user)]
)

# ==============================================================================
# --- User API Key Management Endpoints ---
# ==============================================================================

@router.post("/keys", response_model=models.APIKeyResponse, status_code=status.HTTP_201_CREATED)
def add_api_key_for_current_user(
    key_data: models.APIKeyCreate, 
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(database.get_db)
):
    """
    Allows the current user to add their own API key for a specific provider.
    """
    # The provider must exist globally in the system first.
    provider = crud.get_provider_by_name(db, provider_name=key_data.provider_name)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{key_data.provider_name}' not found. Please contact an admin."
        )

    # Use the new user-centric CRUD function to save the key
    db_key = crud.add_user_api_key(
        db=db,
        user_id=current_user.id,
        provider_name=key_data.provider_name,
        key=key_data.key,
        nickname=key_data.nickname
    )
    return db_key

@router.get("/keys", response_model=List[models.APIKeyResponse])
def list_api_keys_for_current_user(
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(database.get_db)
):
    """
    Lists all API keys that the current user has saved.
    """
    return crud.list_user_api_keys(db=db, user_id=current_user.id)

@router.delete("/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key_for_current_user(
    key_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Deletes one of the current user's own API keys.
    """
    success = crud.delete_user_api_key(db=db, user_id=current_user.id, key_id=key_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API Key with ID {key_id} not found or you do not have permission to delete it."
        )
    return # Return 204 No Content on success


# ==============================================================================
# --- User Model Preference Endpoints ---
# ==============================================================================

@router.put("/models/{model_name}/activate", response_model=models.UserModelPreferenceResponse)
def set_active_model_for_current_user(
    model_name: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Sets the active LLM for the current user's agent.
    """
    preference = crud.set_user_active_model(db=db, user_id=current_user.id, model_name=model_name)
    if not preference:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model with name '{model_name}' not found in the system."
        )
    return preference

@router.get("/models/active", response_model=models.LLMModelResponse)
def get_active_model_for_current_user(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Gets the currently active LLM for the user's agent.
    """
    active_model = crud.get_user_active_model(db=db, user_id=current_user.id)
    if not active_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You have not set an active model. Please choose one."
        )
    return active_model