# src/agent/tools/gmail_watcher.py

from googleapiclient.errors import HttpError
import datetime

from src.core.gcp_auth import build_google_service
from src.core import config
# --- NEW IMPORTS ---
from src.database import crud, database

def watch_gmail_inbox(user_id: int) -> dict:
    """
    This is now an idempotent "Sync & Heal" function.
    1. Checks the database for an active watch.
    2. If active and not expiring soon, it does nothing.
    3. If expired or non-existent, it creates a new one and saves its state.
    4. It always stops any previous watch before starting a new one to prevent ghosts.
    """
    print(f"TOOL: Syncing Gmail watch for user ID: {user_id}")
    db = database.SessionLocal()
    try:
        creds = crud.get_google_credentials_by_user_id(db, user_id)
        if not creds:
            raise Exception("Cannot initiate watch: User has no Google credentials.")

        # Check if a watch is active and not expiring in the next day
        if creds.watch_expiry_timestamp:
            # now = datetime.datetime.now(datetime.timezone.utc)
            now = datetime.datetime.utcnow()

            if creds.watch_expiry_timestamp > (now + datetime.timedelta(days=1)):
                print(f"INFO: Watch is already active for user {user_id}. Expires at {creds.watch_expiry_timestamp}.")
                return {"status": "already_active", "expiry": creds.watch_expiry_timestamp.isoformat()}

        # --- SELF-HEALING ---
        # Before starting a new watch, always try to stop any potential old "ghost" one.
        # This is a robust way to clean up previous, out-of-sync states.
        print(f"INFO: Attempting to stop any existing watch for user {user_id} before starting a new one.")
        _stop_watch_internal(user_id)

        # Now, create the new watch
        service = build_google_service('gmail', 'v1', user_id=user_id)
        request_body = {
            'topicName': f'projects/{config.GCP_PROJECT_ID}/topics/{config.GCP_PUBSUB_TOPIC_ID}'
        }
        response = service.users().watch(userId='me', body=request_body).execute()
        
        # Save the new state to the database
        creds.watch_history_id = response['historyId']
        # Google returns expiration in milliseconds, convert to a proper datetime
        creds.watch_expiry_timestamp = datetime.datetime.fromtimestamp(int(response['expiration']) / 1000, tz=datetime.timezone.utc)
        db.commit()
        
        print(f"SUCCESS: New Gmail watch initiated for user {user_id}. State saved to DB.")
        return response

    finally:
        db.close()

def stop_gmail_inbox_watch(user_id: int) -> bool:
    """
    Stops the watch and clears the state from the database.
    """
    print(f"TOOL: Stopping Gmail watch for user ID: {user_id}")
    db = database.SessionLocal()
    try:
        success = _stop_watch_internal(user_id)
        
        # Clear the state from our database
        creds = crud.get_google_credentials_by_user_id(db, user_id)
        if creds:
            creds.watch_history_id = None
            creds.watch_expiry_timestamp = None
            db.commit()
            print(f"INFO: Watch state cleared from DB for user {user_id}.")
        return success
    finally:
        db.close()

def _stop_watch_internal(user_id: int) -> bool:
    """Internal function to call the Google API to stop the watch."""
    try:
        service = build_google_service('gmail', 'v1', user_id=user_id)
        service.users().stop(userId='me').execute()
        print(f"INFO: Google API confirmed watch stopped for user {user_id}.")
        return True
    except HttpError as error:
        # A 404 error means there was no watch to stop, which is a success for our purposes.
        if error.resp.status == 404:
            print(f"INFO: No active watch found for user {user_id} to stop (This is OK).")
            return True
        print(f"WARN: An HTTP error occurred while stopping Gmail watch for user {user_id}: {error}")
        return False
    except Exception as e:
        print(f"WARN: An unexpected error occurred while stopping watch for user {user_id}: {e}")
        return False