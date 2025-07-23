# File: src/core/gcp_auth.py (Standard Local Server Flow)

import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# File: src/core/gcp_auth.py

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify" # <-- NEW SCOPE for watch() API
]
TOKEN_PATH = "token.json"
CREDS_PATH = "credentials.json"

def get_credentials() -> Credentials:
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, "w") as token:
                token.write(creds.to_json())
        else:
            raise Exception("Authentication required. Please run the `!auth` command.")
            
    return creds

def run_auth_flow() -> Credentials:
    """
    Runs the local server authorization flow. This is the standard, most
    reliable method for Desktop apps.
    """
    if not os.path.exists(CREDS_PATH):
        raise FileNotFoundError(f"CRITICAL: '{CREDS_PATH}' not found.")
    
    flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
    
    # This will print a URL (like http://localhost:12345/) in the console.
    creds = flow.run_local_server(port=0)
    
    with open(TOKEN_PATH, "w") as token:
        token.write(creds.to_json())
    return creds

def build_google_service(service_name: str, version: str):
    creds = get_credentials()
    return build(service_name, version, credentials=creds)