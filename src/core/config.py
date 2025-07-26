# AIBuddies/src/core/config.py
import os
import json 
from dotenv import load_dotenv
from datetime import datetime, date, timezone # Import timezone is good practice but not strictly needed for this file's fix
from src.core.utils import to_rfc3339 # <--- NEW IMPORT

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
    Custom JSON encoder that can serialize datetime and date objects to RFC 3339 strings (ISO 8601 with Z for UTC).
    Ensures datetime objects are timezone-aware and in UTC before serialization.
    """
    def default(self, obj):
        if isinstance(obj, datetime):
            # Ensure datetime is timezone-aware and in UTC before formatting
            return to_rfc3339(obj) # <--- CRITICAL FIX: Use the utility function from src.core.utils
        elif isinstance(obj, date):
            return obj.isoformat() # For date objects, simple isoformat is fine (no time/timezone)
        return json.JSONEncoder.default(self, obj)