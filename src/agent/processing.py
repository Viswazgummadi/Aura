import json
import asyncio
from .tools import gmail as gmail_tool
from src.database import crud, database
from src.api.connection_manager import manager

def process_new_email_notification(email: str, start_history_id: int):
    """
    This function runs in the background. It fetches the new email(s),
    orchestrates AI processing, and sends real-time notifications.
    """
    print(f"BACKGROUND_TASK: Processing started for {email} from historyId {start_history_id}")
    db = database.SessionLocal()
    try:
        # 1. Get the user from the database by their email
        user = crud.get_user_by_email(db, email=email)
        if not user:
            print(f"ERROR: No user found for email {email}. Cannot process notification.")
            return

        # 2. Use the gmail_tool to fetch the actual new message(s)
        new_messages, last_history_id = gmail_tool.fetch_new_messages_for_processing_from_api(
            user_id=user.id,
            start_history_id=start_history_id
        )

        if not new_messages:
            print(f"INFO: No new messages to process for user {user.id}.")
            return

        for message in new_messages:
            print(f"SUCCESS: Fetched new email for user {user.id}: '{message['subject']}'")
            
            # --- This is where the "Agentic Logic" will go in the future ---
            # For now, we are just creating and sending a simple notification.
            # Example:
            # email_body = gmail_tool.get_email_body(user_id=user.id, message_id=message['id'])
            # summary = ai_model.summarize(email_body) 
            # notification_payload = {"type": "email_summary", "data": summary}
            # ---

            # 3. Create the notification payload to send to the client
            notification_payload = {
                "type": "new_email_notification",
                "data": {
                    "id": message.get('id'),
                    "subject": message.get('subject'),
                    "sender": message.get('sender')
                }
            }
            
            # 4. Send the notification via WebSocket
            try:
                # We are in a synchronous function, but manager.send_personal_message is async.
                # asyncio.run() is the bridge that allows us to call and wait for the async code to finish.
                asyncio.run(manager.send_personal_message(
                    json.dumps(notification_payload),
                    user.id
                ))
                print(f"SUCCESS: Sent WebSocket notification to user {user.id}")
            except Exception as e:
                print(f"ERROR: Failed to send WebSocket message to user {user.id}. Details: {e}")

    finally:
        db.close()