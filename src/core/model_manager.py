# src/core/model_manager.py

import google.generativeai as genai
from src.database import crud, database, models

# A simple in-memory cache to store the configured generative model instance
# to avoid re-configuring it on every single call.
_model_instance_cache = {}

class ModelManager:
    def get_active_model(self):
        """
        The primary method the agent will call.
        It retrieves the active model configuration, gets the next available API key,
        configures the client, and returns a ready-to-use model instance.
        """
        db = database.SessionLocal()
        try:
            # 1. Find out which model is active
            active_model_config = crud.get_active_llm_model(db)
            if not active_model_config:
                raise Exception("No active LLM model is configured in the database.")
            
            # Check the cache first. If we already configured this model, reuse it.
            # (Note: In a multi-replica setup, this cache would be external like Redis)
            if active_model_config.name in _model_instance_cache:
                return _model_instance_cache[active_model_config.name]

            # 2. Get the provider for that model
            provider_name = active_model_config.provider.name
            if not provider_name:
                 raise Exception(f"Model {active_model_config.name} has no provider associated with it.")

            # 3. Get the next available, least recently used API key for that provider
            api_key_obj = crud.get_next_api_key(db, provider_name)
            if not api_key_obj:
                raise Exception(f"No active API keys available for the '{provider_name}' provider.")

            # 4. Configure the client for the specific provider
            if provider_name == "google":
                genai.configure(api_key=api_key_obj.key)
                model_instance = genai.GenerativeModel(active_model_config.name)
                
                # Cache the configured instance
                _model_instance_cache[active_model_config.name] = model_instance
                
                print(f"INFO: Configured model '{active_model_config.name}' using API key ID {api_key_obj.id}")
                return model_instance
            
            # (Future) Add logic for other providers like OpenAI
            # elif provider_name == "openai":
            #     # ... configure openai client
            #     pass
            
            else:
                raise NotImplementedError(f"Provider '{provider_name}' is not supported yet.")

        finally:
            db.close()

# Create a single, global instance of the manager for the application to use
model_manager = ModelManager()