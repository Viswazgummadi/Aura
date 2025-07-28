# src/agent/tools/gmail.py

import base64
import email
from email.mime.text import MIMEText
import time
from langchain_core.tools import tool
from typing import List, Dict
from googleapiclient.errors import HttpError
from src.database import crud, database
from src.core.gcp_auth import build_google_service

# ==============================================================================
# === AGENT-FACING TOOLS (@tool decorated) =====================================
# ==============================================================================

@tool
def list_unread_emails(user_id: int, max_results: int = 10) -> List[Dict]:
    """
    Lists the most recent unread emails from the user's inbox.
    Use this to get a quick summary of new emails. Returns a list of dictionaries.
    """
    try:
        service = build_google_service('gmail', 'v1', user_id=user_id)
        results = service.users().messages().list(
            userId='me', labelIds=['INBOX', 'UNREAD'], maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        email_data = []
        if not messages:
            return []

        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id'], format='metadata').execute()
            headers = msg.get('payload', {}).get('headers', [])
            subject = next((i['value'] for i in headers if i['name'] == 'Subject'), 'No Subject')
            sender = next((i['value'] for i in headers if i['name'] == 'From'), 'Unknown Sender')
            email_data.append({'subject': subject, 'sender': sender, 'id': message['id'], 'snippet': msg.get('snippet')})
            
        return email_data
    except Exception as e:
        return [{"error": f"An unexpected error occurred while listing unread emails: {e}"}]

@tool
def get_email_body(user_id: int, message_id: str) -> str:
    """
    Retrieves the full plain text body of a specific email by its ID.
    Use this after finding an important email with `list_unread_emails`.
    """
    try:
        service = build_google_service('gmail', 'v1', user_id=user_id)
        msg_raw = service.users().messages().get(userId='me', id=message_id, format='raw').execute()
        if 'raw' not in msg_raw:
            return "Error: Could not retrieve raw content for this email."

        msg_bytes = base64.urlsafe_b64decode(msg_raw['raw'].encode('ASCII'))
        
        mime_msg = email.message_from_bytes(msg_bytes, policy=email.policy.default)

        for part in mime_msg.walk():
            if part.get_content_maintype() == 'multipart' or part.get('Content-Disposition') is not None:
                continue
            if part.get_content_type() == 'text/plain':
                return part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', 'ignore')

        return "Error: No plain text body found in the email."
    except Exception as e:
        return f"Error: An unexpected error occurred while getting email body: {e}"

@tool
def send_email(user_id: int, to: str, subject: str, body: str) -> Dict:
    """
    Creates and sends a new email from the user's account.
    Returns a dictionary with the sent message details on success.
    """
    try:
        service = build_google_service('gmail', 'v1', user_id=user_id)
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message_body = {'raw': encoded_message}
        sent_message = service.users().messages().send(userId="me", body=create_message_body).execute()
        return sent_message
    except HttpError as e:
        if e.resp.status == 403:
            return {"error": "Permission to send email denied. The 'gmail.send' scope may be missing or revoked."}
        return {"error": f"An API error occurred: {e}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred while sending email: {e}"}

@tool
def mark_email_as_read(user_id: int, message_id: str) -> str:
    """Marks a specific email as read by its ID."""
    try:
        service = build_google_service('gmail', 'v1', user_id=user_id)
        service.users().messages().modify(
            userId='me', id=message_id, body={'removeLabelIds': ['UNREAD']}
        ).execute()
        return f"Success: Message {message_id} marked as read."
    except Exception as e:
        return f"Error: Could not mark message {message_id} as read. {e}"

# ==============================================================================
# === BACKGROUND PROCESSING FUNCTIONS (Not tools) ==============================
# ==============================================================================

def get_latest_history_id_from_gmail_api(user_id: int) -> int:
    # This function is unchanged
    try:
        service = build_google_service('gmail', 'v1', user_id=user_id)
        profile = service.users().getProfile(userId='me').execute()
        return int(profile.get('historyId', 0))
    except Exception as e:
        print(f"ERROR: Could not fetch latest history ID from Gmail profile API for user {user_id}: {e}")
        return 0 

def _get_message_metadata(message_id: str, service, user_id: int) -> dict | None:
    # This function is unchanged
    try:
        msg_metadata = service.users().messages().get(
            userId='me', id=message_id, format='metadata', metadataHeaders=['Subject', 'From', 'Delivered-To']
        ).execute()
        headers = msg_metadata.get('payload', {}).get('headers', [])
        subject = next((i['value'] for i in headers if i['name'] == 'Subject'), 'No Subject')
        sender = next((i['value'] for i in headers if i['name'] == 'From'), 'Unknown Sender')
        delivered_to = next((i['value'] for i in headers if i['name'] == 'Delivered-To'), '').lower()
        return {
            'id': message_id, 'threadId': msg_metadata.get('threadId'), 'subject': subject,
            'sender': sender, 'historyId': int(msg_metadata.get('historyId', 0)),
            'delivered_to': delivered_to
        }
    except HttpError as error:
        if error.resp.status == 404:
            print(f"DEBUG: Message {message_id} not found for user {user_id}. Skipping.")
            return None
        raise
    except Exception as e:
        print(f"ERROR: Failed to get metadata for message {message_id} for user {user_id}: {e}")
        return None

def fetch_new_messages_for_processing_from_api(user_id: int, start_history_id: int | None = None) -> tuple[list, int]:
    """
    This is the core function for the proactive agent.
    It fetches all new history records since the last time it checked.
    """
    db = database.SessionLocal()
    try:
        service = build_google_service('gmail', 'v1', user_id=user_id)
        
        # --- THIS IS THE FIX ---
        # 1. Get the last known history ID FROM OUR DATABASE.
        creds = crud.get_google_credentials_by_user_id(db, user_id)
        if not creds or not creds.watch_history_id:
            raise Exception(f"Cannot fetch new messages: No stored watch_history_id for user {user_id}.")
        
        last_known_history_id = creds.watch_history_id
        print(f"PROACTIVE_AGENT: Last known historyId from DB is {last_known_history_id}.")

        # 2. Fetch all history since that last known point.
        history_response = service.users().history().list(
            userId='me',
            startHistoryId=last_known_history_id,
        ).execute()
        # --- END OF FIX ---
        
        messages_to_process_raw = []
        
        # Process the history records (this part is largely the same)
        history_list = history_response.get('history', [])
        for history_record in history_list:
            messages_in_record = []
            if 'messagesAdded' in history_record:
                messages_in_record.extend([item['message'] for item in history_record['messagesAdded']])
            if 'labelsAdded' in history_record:
                for label_event in history_record['labelsAdded']:
                    if 'INBOX' in label_event.get('labelIds', []):
                         messages_in_record.extend(label_event['messages'])
            processed_ids_in_record = set()
            for message_summary in messages_in_record:
                msg_id = message_summary['id']
                if msg_id in processed_ids_in_record: continue
                processed_ids_in_record.add(msg_id)
                metadata = _get_message_metadata(msg_id, service, user_id)
                if metadata:
                    messages_to_process_raw.append(metadata)
        
        # The new "current" history ID is the one from the history response.
        current_history_id = history_response.get('historyId')
        if current_history_id:
            # 3. IMPORTANT: Update our database with the new latest historyId.
            crud.update_user_watch_history_id(db, user_id, current_history_id)
            print(f"PROACTIVE_AGENT: Updated DB with new historyId {current_history_id} for user {user_id}.")

        messages_to_process_raw.sort(key=lambda x: (x['historyId'], x['id']))
        return messages_to_process_raw, current_history_id

    except HttpError as error:
        # The fallback logic is still valuable
        if error.resp.status == 404 and "startHistoryId" in str(error):
            print(f"WARNING: history.list 404. Performing full unread sync.")
            return _fetch_unread_and_get_history_id_fallback(service, user_id)
        raise
    finally:
        db.close()

def _fetch_messages_from_list_api(service, user_id: int, label_ids: list, max_results: int = 50) -> list:
    # This helper is unchanged
    results = service.users().messages().list(userId='me', labelIds=label_ids, maxResults=max_results).execute()
    return results.get('messages', [])

def _fetch_unread_and_get_history_id_fallback(service, user_id: int) -> tuple[list, int]:
    # This function is unchanged, but we ensure it uses the max_results parameter.
    messages_to_process = []
    highest_history_id_in_fetch = 0
    unread_messages_list = _fetch_messages_from_list_api(service, user_id, label_ids=['INBOX', 'UNREAD'], max_results=50)
    for msg_summary in unread_messages_list:
        metadata = _get_message_metadata(msg_summary['id'], service, user_id)
        if metadata:
            messages_to_process.append(metadata)
            if metadata['historyId'] > highest_history_id_in_fetch:
                highest_history_id_in_fetch = metadata['historyId']
    if not messages_to_process and highest_history_id_in_fetch == 0:
        highest_history_id_in_fetch = get_latest_history_id_from_gmail_api(user_id=user_id)
    messages_to_process.sort(key=lambda x: (x['historyId'], x['id']))
    return messages_to_process, highest_history_id_in_fetch