# File: src/core/model_manager.py

import json
import os
from typing import Dict, Any

from src.core import config

MODELS_FILE = "models.json"

# --- Private Helper Functions ---

def _load_configs() -> Dict[str, Any]:
    """Loads model and key configurations from the JSON file."""
    if not os.path.exists(MODELS_FILE):
        return {}
    try:
        with open(MODELS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def _save_configs(configs: Dict[str, Any]):
    """Saves the configurations to the JSON file."""
    with open(MODELS_FILE, 'w') as f:
        json.dump(configs, f, indent=4)

def _initialize_configs():
    """
    Creates a default models.json from .env variables if it doesn't exist.
    This is called on bot startup.
    """
    if os.path.exists(MODELS_FILE):
        return

    print("INFO: models.json not found. Creating a default configuration from .env file...")
    
    if not config.GOOGLE_API_KEY:
        print("WARNING: GOOGLE_API_KEY not found in .env. Cannot create default model config.")
        return

    default_configs = {
        "active_model_id": "gemini-flash",
        "models": {
            "gemini-flash": {
                "model_name": "gemini-1.5-flash",
                "provider": "google",
                "api_key_id": "google_default"
            }
        },
        "api_keys": {
            "google_default": config.GOOGLE_API_KEY
        }
    }
    _save_configs(default_configs)
    print("INFO: Default models.json created successfully.")

# --- Public Management Functions ---

def add_api_key(key_id: str, key_value: str):
    configs = _load_configs()
    configs.setdefault("api_keys", {})[key_id] = key_value
    _save_configs(configs)

def remove_api_key(key_id: str) -> bool:
    configs = _load_configs()
    if "api_keys" in configs and key_id in configs["api_keys"]:
        del configs["api_keys"][key_id]
        _save_configs(configs)
        return True
    return False

def list_api_keys() -> Dict[str, str]:
    return _load_configs().get("api_keys", {})

def add_model(model_id: str, model_name: str, provider: str, api_key_id: str):
    configs = _load_configs()
    if "api_keys" not in configs or api_key_id not in configs["api_keys"]:
        raise ValueError(f"API Key ID '{api_key_id}' not found. Please add the key first.")
    
    new_model = {
        "model_name": model_name,
        "provider": provider,
        "api_key_id": api_key_id
    }
    configs.setdefault("models", {})[model_id] = new_model
    _save_configs(configs)

def remove_model(model_id: str) -> bool:
    configs = _load_configs()
    if "models" in configs and model_id in configs["models"]:
        if configs.get("active_model_id") == model_id:
            raise ValueError("Cannot delete the currently active model. Please switch to another model first.")
        del configs["models"][model_id]
        _save_configs(configs)
        return True
    return False

def list_models() -> Dict[str, Any]:
    return _load_configs().get("models", {})

def set_active_model(model_id: str):
    configs = _load_configs()
    if "models" not in configs or model_id not in configs["models"]:
        raise ValueError(f"Model ID '{model_id}' not found.")
    
    configs["active_model_id"] = model_id
    _save_configs(configs)

def get_active_config() -> Dict[str, Any] | None:
    """
    Gets the full configuration details for the currently active model.
    """
    configs = _load_configs()
    active_model_id = configs.get("active_model_id")
    if not active_model_id:
        return None

    model_info = configs.get("models", {}).get(active_model_id)
    if not model_info:
        return None

    api_key_id = model_info.get("api_key_id")
    api_key = configs.get("api_keys", {}).get(api_key_id)
    if not api_key:
        return None
        
    return {
        "model_name": model_info["model_name"],
        "api_key": api_key
    }

# --- Initialization ---
_initialize_configs()