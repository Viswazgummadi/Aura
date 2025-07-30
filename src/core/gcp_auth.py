# In src/core/gcp_auth.py

# Keep all your existing imports, then replace the functions:
import os.path
import json
from datetime import datetime, timedelta, timezone
import httpx

from google.oauth2 import id_token
from google.auth.transport import requests
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow
from src.core import config
from src.database import crud, database, models

# SCOPES are unchanged
SCOPES = [
    "openid", "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.settings.basic", "https://www.googleapis.com/auth/gmail.send"
]

def build_google_service(service_name: str, version: str, user_id: int):
    """Builds and returns an authorized Google API service object (REFACTORED)."""
    db = database.SessionLocal()
    try:
        db_creds = crud.get_google_credentials_by_user_id(db, user_id)
        if not db_creds:
            raise Exception(f"No Google credentials for user {user_id}. Please link your Google account.")

        # Build Credentials object directly from the DB columns
        creds = Credentials(
            token=db_creds.access_token,
            refresh_token=db_creds.refresh_token,
            token_uri=db_creds.token_uri,
            client_id=db_creds.client_id,
            client_secret=db_creds.client_secret,
            scopes=db_creds.scopes.split(' '),
            expiry=db_creds.expiry # Already a timezone-aware datetime from DB
        )

        if creds.expired and creds.refresh_token:
            print(f"DEBUG: Google creds for user {user_id} expired. Refreshing...")
            try:
                creds.refresh(GoogleAuthRequest())
                
                # After refresh, the 'creds' object is updated in-place.
                # Now, save these updated values back to the DB.
                updated_creds_data = {
                    "access_token": creds.token,
                    "expiry": creds.expiry,
                    # We don't need to pass the refresh token again, as it doesn't change
                    # and our new CRUD function won't overwrite it with None.
                    "scopes": creds.scopes
                }
                crud.save_or_update_google_credentials(db, user_id, updated_creds_data)
                print(f"DEBUG: Successfully refreshed and saved new token for user {user_id}.")

            except RefreshError as e:
                print(f"ERROR: Failed to refresh Google token for user {user_id}. The refresh token may be invalid. Error: {e}")
                # Optional: Delete the bad credentials so the user is forced to re-authenticate.
                # crud.delete_google_credentials_by_user_id(db, user_id)
                raise Exception("Failed to refresh Google credentials. Please try linking your account again.") from e
        
        elif creds.expired and not creds.refresh_token:
             print(f"ERROR: Google credentials for user {user_id} expired and CANNOT be refreshed (no refresh token).")
             raise Exception("Google credentials expired and cannot be refreshed. Please link your account again.")

        return build(service_name, version, credentials=creds)
    finally:
        db.close()

async def exchange_code_for_token(auth_code: str, state: str, db: AsyncSession) -> models.GoogleCredentials:
    """Exchanges auth code for tokens and saves them to the DB (REFACTORED)."""
    try:
        db_oauth_state = await crud.get_oauth_state_by_value_async(db, state_value=state)
        if not db_oauth_state:
            raise Exception("Invalid or missing OAuth state. Please try logging in again.")

        user_id = db_oauth_state.user_id
        await crud.delete_oauth_state_async(db, state_value=state)

        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": config.GOOGLE_CLIENT_ID, "client_secret": config.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=SCOPES, redirect_uri=config.GOOGLE_REDIRECT_URI
        )
        # This is where the code is exchanged for tokens
        flow.fetch_token(code=auth_code)
        
        # flow.credentials now holds all the token information
        creds = flow.credentials
        
        
        # Verify the ID token to get the user's email securely
        id_info = id_token.verify_oauth2_token(creds.id_token, requests.Request(), creds.client_id)
        google_email = id_info.get('email')

        # Check for the crucial refresh_token
        has_refresh_token = creds.refresh_token is not None
        print(f"DEBUG: Token exchange for user {user_id}. Refresh token received from Google: {has_refresh_token}")
        if not has_refresh_token:
            print("WARNING: No refresh token received. User may need to re-authenticate fully if access is revoked.")
        print("creds.token ---->", creds.token)
        # Prepare data for our new database schema
        creds_data_for_db = {
            "google_email": google_email,
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
            "expiry": creds.expiry, # This is already a timezone-aware datetime
        }
        print("Saving creds_data_for_db:", creds_data_for_db)

        db_creds = await crud.save_or_update_google_credentials_async(db, user_id, creds_data_for_db)
        print(f"DEBUG: Successfully saved credentials to DB for user {user_id} with email {google_email}")
        return db_creds
        
    except Exception as e:
        print(f"ERROR: Google token exchange failed: {e}")
        # Re-raise the exception to be handled by the API endpoint
        raise

def get_google_auth_url(state: str) -> str:
    """Generates the Google Auth URL (REFACTORED to include prompt=consent)."""
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
    
    # THE FIX: Add `prompt='consent'` to ensure a refresh token is always issued.
    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        state=state,
        prompt='consent' 
    )
    return authorization_url
