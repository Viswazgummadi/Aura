# src/core/gcp_auth.py
import os.path
import json
from datetime import datetime, timedelta, timezone
import httpx

# These new imports are for decoding the id_token
from google.oauth2 import id_token
from google.auth.transport import requests

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow
from googleapiclient.errors import HttpError

from src.core import config
from src.database import crud, database, models
from src.core.utils import to_rfc3339

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.settings.basic",
    "https://www.googleapis.com/auth/gmail.send"
]

def build_google_service(service_name: str, version: str, user_id: int):
    """Builds and returns an authorized Google API service object."""
    db = database.SessionLocal()
    try:
        db_creds = crud.get_google_credentials_by_user_id(db, user_id)
        if not db_creds:
            raise Exception(f"No Google credentials for user {user_id}. Link account.")

        token_data = json.loads(db_creds.token)
        expiry_dt_naive = None
        if expiry_str := token_data.get('expiry', ''):
            iso_str = expiry_str.replace("Z", "+00:00")
            aware_dt = datetime.fromisoformat(iso_str)
            expiry_dt_naive = aware_dt.replace(tzinfo=None)

        creds = Credentials(
            token=token_data['access_token'], refresh_token=token_data.get('refresh_token'),
            token_uri=token_data.get('token_uri'), client_id=token_data.get('client_id'),
            client_secret=token_data.get('client_secret'), scopes=token_data.get('scopes', []),
            expiry=expiry_dt_naive
        )

        if creds.expired and creds.refresh_token:
            print(f"DEBUG: Google creds for user {user_id} expired. Refreshing...")
            try:
                creds.refresh(GoogleAuthRequest())
                new_aware_expiry = creds.expiry.replace(tzinfo=timezone.utc)
                updated_token_data = {
                    "access_token": creds.token, "refresh_token": creds.refresh_token,
                    "token_uri": creds.token_uri, "client_id": creds.client_id or config.GOOGLE_CLIENT_ID,
                    "client_secret": creds.client_secret or config.GOOGLE_CLIENT_SECRET,
                    "scopes": creds.scopes, "expiry": new_aware_expiry,
                    "google_email": token_data.get('google_email') # Preserve the email on refresh
                }
                crud.save_google_credentials(db, user_id, updated_token_data)
            except HttpError as e:
                raise Exception("Failed to refresh Google credentials.") from e
        
        elif creds.expired and not creds.refresh_token:
             raise Exception("Google credentials expired and cannot be refreshed.")

        return build(service_name, version, credentials=creds)
    finally:
        db.close()

async def exchange_code_for_token(auth_code: str, state: str) -> models.GoogleCredentials:
    db = database.SessionLocal()
    try:
        db_oauth_state = crud.get_oauth_state_by_value(db, state_value=state)
        if not db_oauth_state:
            raise Exception("Invalid or missing OAuth state.")
        
        user_id_from_state = db_oauth_state.user_id
        crud.delete_oauth_state(db, state_value=state)

        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": auth_code, "client_id": config.GOOGLE_CLIENT_ID,
                    "client_secret": config.GOOGLE_CLIENT_SECRET, "redirect_uri": config.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code"
                }
            )
            token_response.raise_for_status()
            token_data_from_google = token_response.json()
            
            # --- THIS IS THE CORRECTED LOGIC ---
            # 1. First, decode the id_token that Google sent us.
            id_info = id_token.verify_oauth2_token(
                token_data_from_google['id_token'], requests.Request(), config.GOOGLE_CLIENT_ID
            )
            # 2. Extract the user's verified Google email from the decoded token.
            google_email = id_info.get('email')
            if not google_email:
                raise Exception("Could not retrieve email from Google ID token.")
            print(f"INFO: Verified Google email '{google_email}' for user {user_id_from_state}.")
            # --- END OF CORRECTION ---

            expiry_dt = datetime.now(timezone.utc) + timedelta(seconds=token_data_from_google.get('expires_in', 3600))
            
            token_data_for_db = {
                "access_token": token_data_from_google['access_token'],
                "refresh_token": token_data_from_google.get('refresh_token'),
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": config.GOOGLE_CLIENT_ID,
                "client_secret": config.GOOGLE_CLIENT_SECRET,
                "scopes": token_data_from_google.get('scope', '').split(' '),
                "expiry": expiry_dt,
                "google_email": google_email # 3. Now we can safely use the variable here.
            }
        
        db_creds = crud.save_google_credentials(db, user_id_from_state, token_data_for_db)
        return db_creds
    except Exception as e:
        print(f"ERROR: Google token exchange failed: {e}")
        raise
    finally:
        db.close()

def get_google_auth_url(state: str) -> str:
    # This function is unchanged
    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": config.GOOGLE_CLIENT_ID, "client_secret": config.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [config.GOOGLE_REDIRECT_URI],
            }
        },
        scopes=SCOPES, redirect_uri=config.GOOGLE_REDIRECT_URI
    )
    authorization_url, _ = flow.authorization_url(
        access_type='offline', include_granted_scopes='true', state=state
    )
    return authorization_url