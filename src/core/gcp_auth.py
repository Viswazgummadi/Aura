import os.path
import json
from datetime import datetime, timedelta, timezone
import httpx

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow
from googleapiclient.errors import HttpError

from src.core import config
from src.database import crud, database
from src.database import models
from src.core.utils import to_rfc3339 # <-- NEW IMPORT

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.settings.basic",
    "https://www.googleapis.com/auth/gmail.send"
]

def build_google_service(service_name: str, version: str, user_id: int):
    """
    Builds and returns an authorized Google API service object.
    Handles credential loading, parsing, and automated token refreshing.
    """
    db = database.SessionLocal()
    try:
        db_creds = crud.get_google_credentials_by_user_id(db, user_id)
        if not db_creds:
            raise Exception(f"No Google credentials found for user ID {user_id}. Please link your Google account first.")

        token_data = json.loads(db_creds.token)
        expiry_str = token_data.get('expiry', '')
        expiry_dt_naive = None

        if expiry_str:
            # Parse the RFC3339 string from the DB into a timezone-aware datetime object.
            iso_str = expiry_str.replace("Z", "+00:00")
            aware_dt = datetime.fromisoformat(iso_str)
            
            # **CRITICAL FIX**: The google-auth library expects a naive datetime representing UTC.
            # We must remove the timezone info before passing it to the Credentials object.
            expiry_dt_naive = aware_dt.replace(tzinfo=None)

        creds = Credentials(
            token=token_data['access_token'],
            refresh_token=token_data.get('refresh_token'),
            token_uri=token_data.get('token_uri'),
            client_id=token_data.get('client_id'),
            client_secret=token_data.get('client_secret'),
            scopes=token_data.get('scopes', []),
            expiry=expiry_dt_naive  # Pass the naive datetime here
        )

        # Use the library's built-in properties to check for expiry and refresh token.
        # This is more robust than a manual time comparison.
        if creds.expired and creds.refresh_token:
            print(f"DEBUG: Google credentials for user {user_id} are expired. Refreshing...")
            try:
                # The refresh method will update the creds object in-place.
                creds.refresh(Request())
                print(f"SUCCESS: Google credentials for user {user_id} refreshed successfully.")
                
                # The new expiry time from creds.expiry is a naive datetime (in UTC).
                # We need to make it timezone-aware again before converting to RFC3339 for the DB.
                new_aware_expiry = creds.expiry.replace(tzinfo=timezone.utc)
                
                # Prepare the updated token data for saving.
                updated_token_data = {
                    "access_token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_uri": creds.token_uri,
                    "client_id": creds.client_id or config.GOOGLE_CLIENT_ID,
                    "client_secret": creds.client_secret or config.GOOGLE_CLIENT_SECRET,
                    "scopes": creds.scopes,
                    "expiry": new_aware_expiry # Pass the aware datetime to our CRUD function
                }
                
                # Save the newly refreshed credentials back to the database.
                crud.save_google_credentials(db, user_id, updated_token_data)
                print(f"DEBUG: Saved refreshed Google credentials for user {user_id} to the database.")

            except HttpError as e:
                # This can happen if the refresh token is revoked by the user.
                print(f"ERROR: Failed to refresh Google token for user {user_id}. Re-authentication may be required. Details: {e}")
                # Depending on the error, you might want to delete the stored credentials.
                # e.g., if e.resp.status == 401 or 'invalid_grant' in str(e):
                #     crud.delete_google_credentials_by_user_id(db, user_id)
                raise Exception("Failed to refresh Google credentials. Please try linking your account again.") from e
        
        elif creds.expired and not creds.refresh_token:
             raise Exception("Google credentials have expired and cannot be refreshed automatically. Please link your account again.")

        # Build and return the authorized API service client.
        return build(service_name, version, credentials=creds)

    finally:
        db.close()

# --- Functions for the Web Server OAuth Flow (unchanged from previous working version) ---

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
            token_data_from_google = token_response.json()
            
            expiry_dt = datetime.now(timezone.utc) + timedelta(seconds=token_data_from_google.get('expires_in', 3600))
            
            # TRACE_DT: 6. Expiry before saving to DB during initial exchange
            print(f"TRACE_DT: User {user_id_from_state}: expiry_dt generated for saving: {expiry_dt} (type: {type(expiry_dt)}, tzinfo: {expiry_dt.tzinfo}, id_tzinfo: {id(expiry_dt.tzinfo)})")

            token_data_for_db = {
                "access_token": token_data_from_google['access_token'],
                "refresh_token": token_data_from_google.get('refresh_token'),
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": config.GOOGLE_CLIENT_ID,
                "client_secret": config.GOOGLE_CLIENT_SECRET,
                "scopes": token_data_from_google.get('scope', '').split(' '),
                "expiry": expiry_dt # Pass datetime object, will be serialized by crud.py using DateTimeEncoder
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

# get_google_auth_url function (unchanged)
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