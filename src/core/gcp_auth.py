import os.path
import json
from datetime import datetime, timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from src.core import config
from src.database import crud, database
from src.database import models

# functools.partial is no longer needed
# from functools import partial 

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.settings.basic"
]

def build_google_service(service_name: str, version: str, user_id: int):
    # ... (this function is unchanged from previous correct version) ...
    db = database.SessionLocal()
    try:
        db_creds = crud.get_google_credentials_by_user_id(db, user_id)
        if not db_creds:
            raise Exception(f"No Google credentials found for user ID {user_id}. Please link your Google account.")

        creds_dict = json.loads(db_creds.token)
        creds_dict['token'] = creds_dict.get('access_token', creds_dict.get('token'))

        if isinstance(creds_dict.get('expiry'), str):
            creds_dict['expiry'] = datetime.fromisoformat(creds_dict['expiry'])

        creds = Credentials.from_authorized_user_info(creds_dict, SCOPES)

        if not creds.valid and creds.refresh_token:
            print(f"DEBUG: Refreshing Google token for user {user_id}...")
            creds.client_id = db_creds.client_id
            creds.client_secret = db_creds.client_secret
            
            try:
                creds.refresh(Request())
            except Exception as e:
                raise Exception(f"Failed to refresh Google token for user {user_id}: {e}")

            updated_token_data = {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": creds.scopes,
                "expiry": creds.expiry.astimezone(timezone.utc) if creds.expiry else None
            }
            crud.save_google_credentials(db, user_id, updated_token_data)
            print(f"DEBUG: Google token refreshed and saved for user {user_id}.")
        elif not creds.valid and not creds.refresh_token:
             raise Exception(f"Google credentials for user ID {user_id} are expired and cannot be refreshed. Please re-authenticate.")
        
        return build(service_name, version, credentials=creds)
    finally:
        db.close()

# --- Functions for the Web Server OAuth Flow ---

def get_google_auth_url(state: str) -> str:
    # ... (this function is unchanged) ...
    if not all([config.GOOGLE_CLIENT_ID, config.GOOGLE_CLIENT_SECRET, config.GOOGLE_REDIRECT_URI]):
        raise Exception("Google OAuth environment variables (CLIENT_ID, CLIENT_SECRET, REDIRECT_URI) are not set.")

    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": config.GOOGLE_CLIENT_ID,
                "client_secret": config.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": [config.GOOGLE_REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=config.GOOGLE_REDIRECT_URI
    )
    
    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        state=state
    )
    
    print(f"DEBUG: Generated Google Auth URL with state '{state}': {authorization_url}")
    return authorization_url

# NEW HELPER FUNCTION to perform the blocking fetch_token call
def _perform_fetch_token_blocking(flow_instance: Flow, auth_code: str):
    """
    Helper function to perform the blocking flow.fetch_token() call.
    This is designed to be run within concurrent.futures.ThreadPoolExecutor via run_in_executor.
    """
    flow_instance.fetch_token(auth_code)


async def exchange_code_for_token(auth_code: str, state: str) -> models.GoogleCredentials:
    db = database.SessionLocal()
    try:
        db_oauth_state = crud.get_oauth_state_by_value(db, state_value=state)
        if not db_oauth_state:
            raise Exception("Invalid or missing OAuth state. Potential CSRF attack detected.")
        
        user_id_from_state = db_oauth_state.user_id
        crud.delete_oauth_state(db, state_value=state)
        print(f"API: OAuth state '{state}' verified and deleted for user ID: {user_id_from_state}.")

        if not all([config.GOOGLE_CLIENT_ID, config.GOOGLE_CLIENT_SECRET, config.GOOGLE_REDIRECT_URI]):
            raise Exception("Google OAuth environment variables (CLIENT_ID, CLIENT_CLIENT_SECRET, REDIRECT_URI) are not set.") # Corrected variable name in print

        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": config.GOOGLE_CLIENT_ID,
                    "client_secret": config.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "redirect_uris": [config.GOOGLE_REDIRECT_URI],
                }
            },
            scopes=SCOPES,
            redirect_uri=config.GOOGLE_REDIRECT_URI
        )
        
        loop = asyncio.get_running_loop()
        # THE FIX IS HERE: Call the new wrapper function
        await loop.run_in_executor(None, _perform_fetch_token_blocking, flow, auth_code) # <-- CORRECTED CALL

        creds = flow.credentials
        
        token_data_for_db = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
            "expiry": creds.expiry.astimezone(timezone.utc) if creds.expiry else None
        }
        
        db_creds = crud.save_google_credentials(db, user_id_from_state, token_data_for_db)
        print(f"DEBUG: Google credentials saved for user {user_id_from_state}.")
            
        return db_creds
    except Exception as e:
        print(f"ERROR: Google token exchange failed: {e}")
        raise
    finally:
        db.close()

import asyncio