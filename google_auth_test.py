# In google_auth_test.py
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# These are the same settings from your calendar.py
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TOKEN_PATH = "token.json"
CREDS_PATH = "credentials.json"

def main():
    """
    A minimal script to test ONLY the Google Authentication flow.
    """
    print("--- Starting Google Authentication Test ---")
    creds = None

    if not os.path.exists(CREDS_PATH):
        print(f"CRITICAL FAILURE: '{CREDS_PATH}' not found. Cannot proceed.")
        return

    # Delete old token.json to force a fresh login
    if os.path.exists(TOKEN_PATH):
        print(f"Deleting existing '{TOKEN_PATH}' to force a new login.")
        os.remove(TOKEN_PATH)
    
    try:
        print("Attempting to run the authentication flow...")
        flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
        creds = flow.run_local_server(port=0)
        
        # If the line above completes without an error, it worked.
        print("\n✅ SUCCESS! Authentication flow completed.")
        print("A new 'token.json' file has been created successfully.")
        
        # Save the new credentials
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    except Exception as e:
        print(f"\n❌ FAILURE! An error occurred during the authentication flow.")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Details: {e}")

if __name__ == "__main__":
    main()