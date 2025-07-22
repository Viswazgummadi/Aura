# In src/agent/core.py
import google.generativeai as genai
from src.core import config

# Configure the generative AI model with the API key
try:
    genai.configure(api_key=config.GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("Gemini AI model configured successfully.")
except Exception as e:
    print(f"Error configuring Gemini AI: {e}")
    model = None

# This is a regular 'def' function, as it contains no 'await' calls.
# The async magic happens in client.py with run_in_executor.
def get_gemini_response(prompt: str) -> str:
    """
    Gets a response from the Gemini AI model for a given prompt.
    This is a synchronous, blocking function.
    """
    if not model:
        return "Sorry, the AI model is not configured correctly."
    
    try:
        # This is a blocking network call
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"An error occurred while generating AI response: {e}")
        return "Sorry, I had trouble thinking of a response."