import os.path
import json
from datetime import datetime, timedelta, timezone # <-- Added timedelta for expiry calculation
import httpx

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from src.core import config
from src.database import crud, database
from src.database import models

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.settings.basic"
]

def build_google_service(service_name: str, version: str, user_id: int):
    db = database.SessionLocal()
    try:
        db_creds = crud.get_google_credentials_by_user_id(db, user_id)
        if not db_creds:
            raise Exception(f"No Google credentials found for user ID {user_id}. Please link your Google account.")

        # Assume db_creds.token is always a JSON string representing the token data
        creds_json = json.loads(db_creds.token)
        
        creds = Credentials(
            token=creds_json['access_token'], # Extract access_token from the stored JSON
            refresh_token=creds_json.get('refresh_token'),
            token_uri=creds_json.get('token_uri'),
            client_id=creds_json.get('client_id'),
            client_secret=creds_json.get('client_secret'),
            scopes=creds_json.get('scopes', []),
            # Ensure expiry is a datetime object
            expiry=datetime.fromisoformat(creds_json['expiry']) if isinstance(creds_json.get('expiry'), str) else creds_json.get('expiry')
        )

        if not creds.valid and creds.refresh_token:
            print(f"DEBUG: Refreshing Google token for user {user_id}...")
            creds.client_id = db_creds.client_id
            creds.client_secret = db_creds.client_secret
            
            try:
                creds.refresh(Request())
            except Exception as e:
                raise Exception(f"Failed to refresh Google token for user {user_id}: {e}")

            # Prepare token data for storage: ALWAYS as a dictionary for consistency
            updated_token_data = {
                "access_token": creds.token, # Store actual access token as a field in dict
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
            raise Exception("Google OAuth environment variables (CLIENT_ID, CLIENT_SECRET, REDIRECT_URI) are not set.")

        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": auth_code,
                    "client_id": config.GOOGLE_CLIENT_ID,
                    "client_secret": config.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": config.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code"
                }
            )
            token_response.raise_for_status()
            token_data_from_google = token_response.json() # This is the raw dict from Google
            
            # Prepare token data for storage: ALWAYS as a dictionary for consistency
            token_data_for_db = {
                "access_token": token_data_from_google['access_token'],
                "refresh_token": token_data_from_google.get('refresh_token'),
                "token_uri": "https://oauth2.googleapis.com/token", # Standard Google token URI
                "client_id": config.GOOGLE_CLIENT_ID,
                "client_secret": config.GOOGLE_CLIENT_SECRET,
                "scopes": token_data_from_google.get('scope', '').split(' '), # Convert space-separated string to list
                "expiry": datetime.now(timezone.utc) + timedelta(seconds=token_data_from_google.get('expires_in', 3600)) # Calculate expiry
            }
        
        db_creds = crud.save_google_credentials(db, user_id_from_state, token_data_for_db)
        print(f"DEBUG: Google credentials saved for user {user_id_from_state}.")
            
        return db_creds
    except httpx.HTTPStatusError as e:
        print(f"ERROR: HTTP Error during token exchange: {e.response.status_code} - {e.response.text}")
        raise Exception(f"Failed to exchange Google authorization code: HTTP Error {e.response.status_code}")
    except Exception as e:
        print(f"ERROR: Google token exchange failed: {e}")
        raise
    finally:
        db.close()