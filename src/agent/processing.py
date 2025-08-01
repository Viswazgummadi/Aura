# src/agent/processing.py

from sqlalchemy.orm import Session
from src.database import crud, database
from src.core.gcp_auth import build_google_service

def process_new_email_notification(email: str, new_history_id: str):
    """
    This is the core background task for processing a Gmail push notification.
    It runs after the webhook has already returned a 204 response to Google.
    
    Args:
        email (str): The user's Google email address, from the notification payload.
        new_history_id (str): The new historyId from the notification. This is
                              our new "bookmark" for the user's mailbox state.
    """
    print(f"--- Starting background processing for {email} with new historyId {new_history_id} ---")
    
    # Background tasks don't have access to FastAPI's dependency injection.
    # We must create our own database session and ensure it's closed properly.
    db: Session = database.SessionLocal()
    try:
        # 1. Find our user in the database using their Google email.
        # This requires a CRUD function `get_user_by_google_email`.
        user = crud.get_user_by_google_email(db, google_email=email)
        if not user:
            print(f"ERROR: Received notification for '{email}', but no matching user found in our system.")
            return

        # 2. Get the user's credentials, which includes the last known historyId.
        creds = crud.get_google_credentials_by_user_id(db, user_id=user.id)
        if not creds or not creds.watch_history_id:
            print(f"ERROR: User {user.id} received a notification but is not configured for watching.")
            return
        
        last_known_history_id = creds.watch_history_id

        # 3. Get an authenticated Gmail API service for this user.
        service = build_google_service('gmail', 'v1', user_id=user.id, db_session=db)
        if not service:
            print(f"ERROR: Could not get Gmail service for user {user.id}.")
            return

        # 4. Use the history.list() method to get all changes since our last bookmark.
        print(f"Fetching history for user {user.id} from ID {last_known_history_id}...")
        history_response = service.users().history().list(
            userId='me',
            startHistoryId=last_known_history_id,
            historyTypes=['messageAdded'] # We only care about new messages for now.
        ).execute()

        # 5. Process the changes.
        history_records = history_response.get('history', [])
        new_message_ids = []
        for record in history_records:
            messages_added = record.get('messagesAdded', [])
            for message_info in messages_added:
                new_message_ids.append(message_info['message']['id'])
        
        if not new_message_ids:
            print(f"INFO: Notification received for {email}, but no new messages found in history check. Likely a non-message event.")
        else:
            print(f"SUCCESS: Found {len(new_message_ids)} new message(s) for user {user.id} ({email}).")
            # --- AGENT ACTION ---
            # Fetch and print the subject of each new email.
            for msg_id in new_message_ids:
                msg = service.users().messages().get(userId='me', id=msg_id, format='metadata', metadataHeaders=['Subject', 'From']).execute()
                payload = msg.get('payload', {})
                headers = payload.get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'No Sender')
                print(f"  -> New Email: From: {sender} | Subject: {subject}")
                
                # TODO: In the future, this is where you'd call the agent.

        # 6. CRITICAL: Update the user's historyId in the DB to the new one.
        # This moves our "bookmark" forward so we don't process these changes again.
        creds.watch_history_id = new_history_id
        db.commit()
        
        print(f"Updated historyId for user {user.id} to {new_history_id}")

    except Exception as e:
        print(f"CRITICAL ERROR during background processing for {email}: {e}")
        # Consider adding more robust error logging here.
    finally:
        # 7. Always close the database session.
        db.close()
        print(f"--- Finished background processing for {email} ---")