import os
import json 
from dotenv import load_dotenv
from datetime import datetime, date
# This line finds the .env file in your project folder and loads its contents
load_dotenv()

# Load JWT Secret Key (from .env)
# This will be used in src.core.security
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    print("CRITICAL WARNING: SECRET_KEY not found in .env. JWTs will not work securely.")
    SECRET_KEY = "insecure-default-key" # Fallback for development, DO NOT USE IN PROD

# Load Google API Key (for direct API access, e.g., for Gemini if not using OAuth)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("CRITICAL WARNING: GOOGLE_API_KEY not found in .env file.")

# --- NEW: Load Google OAuth Client Credentials ---
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
GCP_PROJECT_ID=os.getenv("GCP_PROJECT_ID")
GCP_PUBSUB_TOPIC_ID=os.getenv("GCP_PUBSUB_TOPIC_ID")
if not all([GCP_PROJECT_ID, GCP_PUBSUB_TOPIC_ID]):
    print("WARNING: GCP_PROJECT_ID or GCP_PUBSUB_TOPIC_ID not found in .env. Gmail Watcher may not work.")
if not all([GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI]):
    print("CRITICAL WARNING: Google OAuth Client ID, Client Secret, or Redirect URI not found in .env. Google OAuth will not work.")
class DateTimeEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that can serialize datetime and date objects to ISO 8601 strings.
    """
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)