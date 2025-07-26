import os.path
import json
from datetime import datetime, timedelta, timezone
import httpx

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow

from src.core import config
from src.database import crud, database
from src.database import models
from src.core.utils import to_rfc3339 # <-- NEW IMPORT

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

        # TRACE_DT: 1. Before JSON load from DB
        print(f"TRACE_DT: User {user_id}: Raw token string from DB: {db_creds.token[:200]}...") # Print first 200 chars for brevity

        creds_data_from_db = json.loads(db_creds.token)
        
        # TRACE_DT: 2. After JSON load, before parsing expiry
        expiry_str_from_db = creds_data_from_db.get('expiry')
        print(f"TRACE_DT: User {user_id}: 'expiry' string from JSON: {expiry_str_from_db} (type: {type(expiry_str_from_db)})")
        
        # --- START: MORE DETAILED STRING INSPECTION & FALLBACK PARSING ---
        if isinstance(expiry_str_from_db, str):
            print(f"TRACE_DT: User {user_id}: repr(expiry_str_from_db): {repr(expiry_str_from_db)}")
            print(f"TRACE_DT: User {user_id}: len(expiry_str_from_db): {len(expiry_str_from_db)}")
            char_codes = [str(ord(c)) for c in expiry_str_from_db]
            print(f"TRACE_DT: User {user_id}: Char codes: {','.join(char_codes)}")
        # --- END: MORE DETAILED STRING INSPECTION ---

        expiry_dt_from_db = None
        if isinstance(expiry_str_from_db, str) and expiry_str_from_db:
            # First attempt with fromisoformat
            try:
                expiry_dt_from_db = datetime.fromisoformat(expiry_str_from_db.replace("Z", "+00:00"))
                print(f"TRACE_DT: User {user_id}: fromisoformat SUCCESS: {expiry_dt_from_db} (tzinfo: {expiry_dt_from_db.tzinfo}, id_tzinfo: {id(expiry_dt_from_db.tzinfo) if expiry_dt_from_db.tzinfo else 'N/A'})")
            except ValueError as ve:
                print(f"TRACE_DT: User {user_id}: fromisoformat FAILED (ValueError): {ve}")
                # --- FALLBACK TO STRPTIME ---
                # Pattern for 'YYYY-MM-DDTHH:MM:SS.ffffffZ'
                # Remove 'Z' for strptime, then add UTC tzinfo
                if expiry_str_from_db.endswith('Z'):
                    strptime_string = expiry_str_from_db[:-1]
                else:
                    strptime_string = expiry_str_from_db
                
                try:
                    expiry_dt_from_db = datetime.strptime(strptime_string, '%Y-%m-%dT%H:%M:%S.%f')
                    # strptime returns naive, so make it aware with UTC
                    expiry_dt_from_db = expiry_dt_from_db.replace(tzinfo=timezone.utc)
                    print(f"TRACE_DT: User {user_id}: strptime SUCCESS (fallback): {expiry_dt_from_db} (tzinfo: {expiry_dt_from_db.tzinfo}, id_tzinfo: {id(expiry_dt_from_db.tzinfo)})")
                except ValueError as ve_strptime:
                    print(f"TRACE_DT: User {user_id}: strptime FAILED (ValueError): {ve_strptime}")
                    expiry_dt_from_db = None # Both fromisoformat and strptime failed
                except Exception as e_strptime:
                    print(f"TRACE_DT: User {user_id}: strptime FAILED (Unexpected Error): {e_strptime}")
                    expiry_dt_from_db = None
                # --- END FALLBACK ---
            except Exception as e:
                print(f"TRACE_DT: User {user_id}: fromisoformat FAILED (Unexpected Error): {e}")
                expiry_dt_from_db = None

            # Apply timezone standardization only if successfully parsed by any method
            if expiry_dt_from_db is not None:
                # Ensure expiry is explicitly timezone.utc, converting if necessary
                expiry_dt_from_db = expiry_dt_from_db.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
                print(f"TRACE_DT: User {user_id}: expiry_dt_from_db after final TZ standardization: {expiry_dt_from_db} (tzinfo: {expiry_dt_from_db.tzinfo}, id_tzinfo: {id(expiry_dt_from_db.tzinfo)})")
        else:
            print(f"TRACE_DT: User {user_id}: 'expiry' from DB is not a string or is empty: {expiry_str_from_db}")

        # TRACE_DT: 4. Final expiry passed to Credentials constructor
        print(f"TRACE_DT: User {user_id}: Final expiry passed to Credentials: {expiry_dt_from_db} (type: {type(expiry_dt_from_db)}, tzinfo: {expiry_dt_from_db.tzinfo if expiry_dt_from_db else 'N/A'})")
        # Also print id of timezone.utc to compare
        print(f"TRACE_DT: User {user_id}: ID of datetime.timezone.utc: {id(timezone.utc)}")


        creds = Credentials(
            token=creds_data_from_db['access_token'],
            refresh_token=creds_data_from_db.get('refresh_token'),
            token_uri=creds_data_from_db.get('token_uri'),
            client_id=creds_data_from_db.get('client_id'),
            client_secret=creds_data_from_db.get('client_secret'),
            scopes=creds_data_from_db.get('scopes', []),
            expiry=expiry_dt_from_db
        )
        
        # TRACE_DT: 5. Before creds.valid check
        current_time_utc = datetime.now(timezone.utc)
        if not creds.expiry:
            raise Exception("Google credential expiry is missing or failed to parse.")

        print(f"TRACE_DT: User {user_id}: Creds object expiry: {creds.expiry} (type: {type(creds.expiry)}, tzinfo: {creds.expiry.tzinfo}, id_tzinfo: {id(creds.expiry.tzinfo) if creds.expiry else 'N/A'})")
        print(f"TRACE_DT: User {user_id}: Current time (UTC): {current_time_utc} (type: {type(current_time_utc)}, tzinfo: {current_time_utc.tzinfo}, id_tzinfo: {id(current_time_utc.tzinfo)})")
        # Now, for good measure, we'll explicitly try a comparison with `is` for tzinfo objects
        if creds.expiry and current_time_utc:
            print(f"TRACE_DT: User {user_id}: Are tzinfo objects IDENTICAL? {creds.expiry.tzinfo is current_time_utc.tzinfo}")


        if not creds.valid and creds.refresh_token:
            print(f"DEBUG: Refreshing Google token for user {user_id}...")
            creds.client_id = db_creds.client_id
            creds.client_secret = db_creds.client_secret
            
            try:
                creds.refresh(Request())
            except Exception as e:
                raise Exception(f"Failed to refresh Google token for user {user_id}: {e}")

            updated_token_data = {
                "access_token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": config.GOOGLE_CLIENT_ID, # Corrected: use config.GOOGLE_CLIENT_ID
                "client_secret": config.GOOGLE_CLIENT_SECRET, # Corrected: use config.GOOGLE_CLIENT_SECRET
                "scopes": creds.scopes,
                "expiry": creds.expiry.astimezone(timezone.utc).isoformat() if creds.expiry else None
            }
            crud.save_google_credentials(db, user_id, updated_token_data) 
            print(f"DEBUG: Google token refreshed and saved for user {user_id}.")
        elif not creds.valid and not creds.refresh_token:
             raise Exception(f"Google credentials for user ID {user_id} are expired and cannot be refreshed. Please re-authenticate.")
        
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