# File: src/core/model_manager.py

from langchain_google_genai import ChatGoogleGenerativeAI
from src.database import crud, database

class ModelManager:
    def __init__(self):
        """
        The cache now stores instances keyed by a user-model combination
        to ensure user-specific configurations are respected.
        Format: f"user_{user_id}_model_{model_name}"
        """
        self._model_instance_cache = {}

    def get_user_model(self, user_id: int):
        """
        The primary method the agent will call.
        It retrieves the active model configuration AND API key for a SPECIFIC user,
        configures the client, and returns a ready-to-use model instance.
        """
        db = database.SessionLocal()
        try:
            # 1. Find out which model is active for THIS user.
            active_model_config = crud.get_user_active_model(db, user_id=user_id)
            if not active_model_config:
                raise Exception(f"User {user_id} has not configured an active LLM model.")
            
            # 2. Check the instance cache first.
            cache_key = f"user_{user_id}_model_{active_model_config.name}"
            if cache_key in self._model_instance_cache:
                return self._model_instance_cache[cache_key]

            # 3. Get the provider for that model.
            provider_name = active_model_config.provider.name
            if not provider_name:
                 raise Exception(f"Model {active_model_config.name} has no provider.")

            # 4. Get the API key for THIS user and THIS provider.
            api_key_obj = crud.get_user_api_key_for_provider(db, user_id=user_id, provider_name=provider_name)
            if not api_key_obj:
                raise Exception(f"User {user_id} has no active API key for the '{provider_name}' provider.")

            # 5. Configure the client for the specific provider using the user's key.
            if provider_name == "google":
                model_instance = ChatGoogleGenerativeAI(
                    model=active_model_config.name,
                    google_api_key=api_key_obj.key,
                    convert_system_message_to_human=True
                )
                
                # Cache the configured instance with the user-specific key.
                self._model_instance_cache[cache_key] = model_instance
                
                print(f"INFO: [User {user_id}] Configured model '{active_model_config.name}' using their API key ID {api_key_obj.id}")
                return model_instance
            
            else:
                raise NotImplementedError(f"Provider '{provider_name}' is not supported yet.")

        finally:
            db.close()

# Keep a clear, distinct name for the global instance.
llm_manager = ModelManager()

# The helper function now needs the user_id to pass along.
def get_model_for_user(user_id: int):
    """A simple helper to get the active model for a specific user."""
    return llm_manager.get_user_model(user_id)