# File: src/agent/core.py (Simplified and Final)

from langchain_google_genai import ChatGoogleGenerativeAI
from src.core import model_manager

# --- Global Model Object ---
model = None

def create_llm_instance():
    """
    Creates or reloads the global 'model' instance based on the active
    configuration in models.json.
    """
    global model
    
    print("--- Loading LLM instance ---")
    
    active_config = model_manager.get_active_config()
    
    if not active_config:
        print("CRITICAL: No active model configuration found. Agent will not work.")
        model = None
        return

    model_name = active_config["model_name"]
    api_key = active_config["api_key"]

    try:
        # Instantiate the model without the problematic safety_settings
        model = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            convert_system_message_to_human=True
        )
        print(f"✅ Successfully loaded model '{model_name}'.")
    except Exception as e:
        print(f"❌ Error configuring Gemini AI via LangChain: {e}")
        model = None

# --- Initial Load ---
create_llm_instance()