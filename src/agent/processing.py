# File: src/agent/processing.py

from sqlalchemy.orm import Session
from src.database import crud, database
from src.core.gcp_auth import build_google_service
from googleapiclient.errors import HttpError
from datetime import datetime
# --- NEW: Import a library for parsing email dates ---
from email.utils import parsedate_to_datetime

def process_new_email_notification(email: str, new_history_id: str):
    """
    This background task fetches rich context for new emails and prepares
    them for the agent, with improved logging and structure.
    """
    print(f"--- [START] Processing notification for {email} (History ID: {new_history_id}) ---")
    
    db: Session = database.SessionLocal()
    try:
        user = crud.get_user_by_google_email(db, google_email=email)
        if not user:
            print(f"  [ERROR] No matching user found for '{email}'. Aborting.")
            return

        creds = crud.get_google_credentials_by_user_id(db, user_id=user.id)
        if not creds or not creds.watch_history_id:
            print(f"  [ERROR] User {user.id} is not configured for watching. Aborting.")
            return
        
        last_known_history_id = creds.watch_history_id
        service = build_google_service('gmail', 'v1', user_id=user.id)
        if not service:
            print(f"  [ERROR] Could not get Gmail service for user {user.id}. Aborting.")
            return

        print(f"  [INFO] Fetching history since last check (ID: {last_known_history_id})...")
        history_response = service.users().history().list(
            userId='me', startHistoryId=last_known_history_id, historyTypes=['messageAdded']
        ).execute()

        # We will collect structured context objects for each new email
        messages_to_process = []
        history_records = history_response.get('history', [])
        for record in history_records:
            messages_added = record.get('messagesAdded', [])
            for message_info in messages_added:
                messages_to_process.append(message_info['message']['id'])
        
        if not messages_to_process:
            print(f"  [INFO] Notification received, but no 'messageAdded' events found. Likely a non-message event (e.g., label change).")
        else:
            print(f"  [SUCCESS] Found {len(messages_to_process)} new message(s). Fetching details...")
            
            # --- AGENT CONTEXT PREPARATION ---
            for i, msg_id in enumerate(messages_to_process, 1):
                try:
                    # Fetch more metadata for richer context
                    msg = service.users().messages().get(
                        userId='me', id=msg_id, format='metadata', 
                        metadataHeaders=['Subject', 'From', 'To', 'Date', 'Message-ID']
                    ).execute()

                    headers = msg.get('payload', {}).get('headers', [])
                    
                    # Create a rich context dictionary for the agent
                    date_str = next((h['value'] for h in headers if h['name'].lower() == 'date'), None)
                    
                    email_context = {
                        "user_id": user.id,
                        "message_id": msg.get("id"),
                        "thread_id": msg.get("threadId"),
                        "subject": next((h['value'] for h in headers if h['name'].lower() == 'subject'), '[No Subject]'),
                        "sender": next((h['value'] for h in headers if h['name'].lower() == 'from'), '[No Sender]'),
                        "recipient": next((h['value'] for h in headers if h['name'].lower() == 'to'), '[No Recipient]'),
                        "timestamp_utc": parsedate_to_datetime(date_str) if date_str else None,
                        "internal_date": datetime.fromtimestamp(int(msg['internalDate']) / 1000) # Google's internal timestamp
                    }

                    # This is the point where the agent gets the data
                    print(f"    - Email [{i}/{len(messages_to_process)}]: From: {email_context['sender']}, Subject: {email_context['subject']}")
                    
                    # TODO: Replace the print with your agent logic
                    # agent.handle_new_email(email_context)
                    # For example, you could save `email_context` to a new table in your database.

                except HttpError as error:
                    if error.resp.status == 404:
                        print(f"    - Email [{i}/{len(messages_to_process)}]: [SKIPPED] Message with ID {msg_id} was not found (likely deleted).")
                        continue
                    else:
                        raise error # Let the outer block handle other API errors

        # CRITICAL: Update the historyId bookmark, even if no new messages were found.
        # This acknowledges we've processed up to this point in the mailbox's history.
        creds.watch_history_id = new_history_id
        db.commit()
        print(f"  [STATE UPDATE] New historyId {new_history_id} saved for user {user.id}.")

    except Exception as e:
        print(f"  [CRITICAL] An unhandled exception occurred: {e}")
    finally:
        db.close()
        print(f"--- [END] Processing for {email} (History ID: {new_history_id}) ---")