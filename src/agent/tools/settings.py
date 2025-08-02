# File: src/agent/tools/settings.py

from langchain_core.tools import tool
from typing import Dict, Optional, List
from src.database import crud, database, models

@tool
def set_active_model(model_name: str, **kwargs) -> Dict:
    """
    Sets the active LLM for the current user's agent.
    Use this when the user asks to change or switch their model.
    """
    db = database.SessionLocal()
    try:
        user_id = kwargs.get("user_id")
        if user_id is None:
            raise ValueError("set_active_model tool was called without a user_id.")

        preference = crud.set_user_active_model(db=db, user_id=user_id, model_name=model_name)
        if not preference:
            return {"error": f"Model with name '{model_name}' not found in the system."}

        return {"status": "success", "message": f"Active model has been set to {model_name}."}
    finally:
        db.close()

@tool
def get_my_active_model(**kwargs) -> Dict:
    """
    Gets the currently active LLM for the user's agent.
    Use this if the user asks 'what model are we using?' or similar questions.
    """
    db = database.SessionLocal()
    try:
        user_id = kwargs.get("user_id")
        if user_id is None:
            raise ValueError("get_my_active_model tool was called without a user_id.")

        active_model = crud.get_user_active_model(db=db, user_id=user_id)
        if not active_model:
            return {"error": "You have not set an active model."}

        return {
            "active_model": active_model.name,
            "provider": active_model.provider.name
        }
    finally:
        db.close()

# Manually create the __tools__ list for robust discovery
__tools__ = [set_active_model, get_my_active_model]