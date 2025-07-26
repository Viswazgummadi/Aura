import base64
import email
from email import policy
import time
from datetime import datetime, timedelta, timezone
from googleapiclient.errors import HttpError

from src.core.gcp_auth import build_google_service # <-- Already imported

# --- Public Tool Functions for Gmail ---

def fetch_unread_emails(user_id: int, max_results: int = 5) -> list: # <-- NEW: user_id argument
    """
    Fetches unread emails from the user's inbox.
    
    Args:
        user_id (int): The ID of the AIBuddies user whose Gmail to access.
        max_results (int): The maximum number of unread emails to retrieve.

    Returns:
        list: A list of email metadata (subject, sender).
    """
    print(f"TOOL: fetch_unread_emails called for user ID: {user_id}")
    try:
        # Pass the user_id to build_google_service
        service = build_google_service('gmail', 'v1', user_id=user_id)
        
        results = service.users().messages().list(
            userId='me', 
            labelIds=['INBOX', 'UNREAD'], 
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        email_data = []

        if not messages:
            return []

        for message in messages:
            msg = service.users().messages().get(
                userId='me', id=message['id'], format='metadata'
            ).execute()
            
            headers = msg.get('payload', {}).get('headers', [])
            subject = next((i['value'] for i in headers if i['name'] == 'Subject'), 'No Subject')
            sender = next((i['value'] for i in headers if i['name'] == 'From'), 'Unknown Sender')
            
            email_data.append({'subject': subject, 'sender': sender, 'id': message['id']}) # Also include ID
            
        return email_data
    except Exception as e:
        print(f"An error occurred in fetch_unread_emails for user {user_id}: {e}")
        raise e
    
def get_email_body(user_id: int, message_id: str) -> str | None: # <-- NEW: user_id argument
    """
    Retrieves the plain text body of an email.
    
    Args:
        user_id (int): The ID of the AIBuddies user whose Gmail to access.
        message_id (str): The ID of the email message.

    Returns:
        str | None: The plain text body of the email, or None if not found.
    """
    print(f"TOOL: get_email_body called for user ID: {user_id}, message ID: {message_id}")
    try:
        # Pass the user_id to build_google_service
        service = build_google_service('gmail', 'v1', user_id=user_id)
        
        msg_raw = service.users().messages().get(
            userId='me', id=message_id, format='raw'
        ).execute()

        if 'raw' not in msg_raw:
            return None

        msg_bytes = base64.urlsafe_b64decode(msg_raw['raw'].encode('ASCII'))
        mime_msg = email.message_from_bytes(msg_bytes, policy=policy.default)

        for part in mime_msg.walk():
            if part.get_content_maintype() == 'multipart' or part.get('Content-Disposition') is not None:
                continue

            if part.get_content_type() == 'text/plain':
                return part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', 'ignore')

        if mime_msg.get_content_type() == 'text/plain':
             return mime_msg.get_payload(decode=True).decode(mime_msg.get_content_charset() or 'utf-8', 'ignore')

        return None
        
    except Exception as e:
        print(f"An error occurred in get_email_body for user {user_id}, message {message_id}: {e}")
        raise e

def mark_message_as_read(user_id: int, message_id: str): # <-- NEW: user_id argument
    """
    Marks an email message as read.
    
    Args:
        user_id (int): The ID of the AIBuddies user whose Gmail to access.
        message_id (str): The ID of the email message to mark as read.
    """
    print(f"TOOL: mark_message_as_read called for user ID: {user_id}, message ID: {message_id}")
    try:
        # Pass the user_id to build_google_service
        service = build_google_service('gmail', 'v1', user_id=user_id)
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        print(f"DEBUG: Message {message_id} marked as read for user {user_id}.")
    except Exception as e:
        print(f"WARNING: Could not mark message {message_id} as read for user {user_id}: {e}")

def get_latest_history_id_from_gmail_api(user_id: int) -> int: # <-- NEW: user_id argument
    """
    Retrieves the latest history ID from the Gmail API for a specific user.
    Used for tracking changes in Gmail.
    """
    print(f"TOOL: get_latest_history_id_from_gmail_api called for user ID: {user_id}")
    try:
        # Pass the user_id to build_google_service
        service = build_google_service('gmail', 'v1', user_id=user_id)
        profile = service.users().getProfile(userId='me').execute()
        return int(profile.get('historyId', 0))
    except Exception as e:
        print(f"ERROR: Could not fetch latest history ID from Gmail profile API for user {user_id}: {e}")
        return 0 

def _get_message_metadata(message_id: str, service, user_id: int) -> dict | None: # <-- NEW: user_id argument
    """
    Helper function to get metadata for a specific message.
    """
    # This helper function now also takes user_id for consistency and future debugging if needed
    try:
        msg_metadata = service.users().messages().get(
            userId='me', id=message_id, format='metadata', metadataHeaders=['Subject', 'From', 'Delivered-To']
        ).execute()
        
        headers = msg_metadata.get('payload', {}).get('headers', [])
        subject = next((i['value'] for i in headers if i['name'] == 'Subject'), 'No Subject')
        sender = next((i['value'] for i in headers if i['name'] == 'From'), 'Unknown Sender')
        delivered_to = next((i['value'] for i in headers if i['name'] == 'Delivered-To'), '').lower()

        return {
            'id': message_id,
            'threadId': msg_metadata.get('threadId'),
            'subject': subject,
            'sender': sender,
            'historyId': int(msg_metadata.get('historyId', 0)),
            'delivered_to': delivered_to
        }
    except HttpError as error:
        if error.resp.status == 404:
            print(f"DEBUG: Message {message_id} not found (might be deleted) for user {user_id}. Skipping.")
            return None
        raise
    except Exception as e:
        print(f"ERROR: Failed to get metadata for message {message_id} for user {user_id}: {e}")
        return None

def fetch_new_messages_for_processing_from_api(
    user_id: int, # <-- NEW: user_id argument
    start_history_id: int | None = None
) -> tuple[list, int]:
    """
    Fetches new Gmail messages for a user using the history API.
    """
    print(f"TOOL: fetch_new_messages_for_processing_from_api called for user ID: {user_id}, start_history_id: {start_history_id}")
    # Pass the user_id to build_google_service
    service = build_google_service('gmail', 'v1', user_id=user_id)
    
    current_gmail_api_history_id = get_latest_history_id_from_gmail_api(user_id=user_id) # <-- Pass user_id
    messages_to_process_raw = []
    
    effective_start_history_id = start_history_id if start_history_id is not None else 0

    print(f"DEBUG: fetch_new_messages_for_processing_from_api: Current Gmail API history for user {user_id}: {current_gmail_api_history_id}, Tracker's effective start: {effective_start_history_id}")

    if effective_start_history_id >= current_gmail_api_history_id:
        print(f"DEBUG: fetch_new_messages_for_processing_from_api: Tracker historyId ({effective_start_history_id}) is not older than current Gmail history ({current_gmail_api_history_id}). No new history to fetch.")
        return [], current_gmail_api_history_id

    try:
        next_page_token = None
        
        while True:
            history_response = service.users().history().list(
                userId='me',
                startHistoryId=effective_start_history_id,
                pageToken=next_page_token,
            ).execute()

            history_list = history_response.get('history', [])
            
            if not history_list and not history_response.get('nextPageToken'):
                break 
            
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
                    
                    if msg_id in processed_ids_in_record:
                        continue
                    processed_ids_in_record.add(msg_id)

                    # IMPORTANT: gmail_history_tracker needs to be multi-user aware.
                    # This is a limitation of the current gmail_history_tracker.py
                    # which is a single file-based storage. For now, it might only
                    # work for one primary user's history, or we need to pass user_id to it.
                    # We will address gmail_history_tracker in Phase 9 (Webhooks)
                    # For now, we assume this is only for the "initial sync" logic
                    # and will update the tracker with a user_id later if needed.
                    
                    # For a basic test, we bypass tracker's is_message_processed check here,
                    # and rely on the full API for this initial phase.
                    # When we integrate the full sync later, we'll need to adapt the tracker.
                    
                    metadata = _get_message_metadata(msg_id, service, user_id) # <-- Pass user_id

                    if metadata: # Removed the 'delivered_to' check for initial sync
                        messages_to_process_raw.append(metadata)
                        print(f"SUCCESS: Found new mail '{metadata['subject']}' (ID: {msg_id}) for user {user_id}. Queued for notification.")
                    else:
                        print(f"DEBUG: SKIPPED message {msg_id} for user {user_id} because metadata was None.")

            next_page_token = history_response.get('nextPageToken')
            if not next_page_token:
                break
            time.sleep(0.1) 

        messages_to_process_raw.sort(key=lambda x: (x['historyId'], x['id']))
        
        print(f"DEBUG: fetch_new_messages_for_processing_from_api: Total {len(messages_to_process_raw)} raw messages fetched via history API for user {user_id}.")
        
        return messages_to_process_raw, current_gmail_api_history_id
    
    except HttpError as error:
        if error.resp.status == 404 and "startHistoryId" in str(error):
            print(f"WARNING: history.list 404 for startHistoryId {effective_start_history_id} for user {user_id}. History too old or invalid. Performing full unread sync to re-establish base. Error: {error._get_reason()}")
            return _fetch_unread_and_get_history_id_fallback(service, user_id) # <-- Pass user_id
        raise
    except Exception as e:
        print(f"An unexpected error occurred in fetch_new_messages_for_processing_from_api for user {user_id}: {e}")
        raise e

def _fetch_messages_from_list_api(service, user_id: int, label_ids: list, max_results: int = 50) -> list: # <-- NEW: user_id argument
    # Helper for fallback, also updated
    # This also needs the user_id, pass it for consistency although not used directly here
    results = service.users().messages().list(
        userId='me', 
        labelIds=label_ids, 
        maxResults=max_results
    ).execute()
    return results.get('messages', [])

def _fetch_unread_and_get_history_id_fallback(service, user_id: int) -> tuple[list, int]: # <-- NEW: user_id argument
    messages_to_process = []
    highest_history_id_in_fetch = 0

    print(f"DEBUG: Performing unread list sync as fallback for user {user_id}.")
    unread_messages_list = _fetch_messages_from_list_api(service, user_id, label_ids=['INBOX', 'UNREAD'], max_results=50) 
    
    for msg_summary in unread_messages_list:
        metadata = _get_message_metadata(msg_summary['id'], service, user_id) # <-- Pass user_id
        if metadata: # Removed the 'delivered_to' check for initial sync
            # For a basic test, we bypass tracker's is_message_processed check here.
            # It will be crucial to revisit this with a multi-user aware tracker.
            messages_to_process.append(metadata)
            if metadata['historyId'] > highest_history_id_in_fetch:
                highest_history_id_in_fetch = metadata['historyId']
            print(f"DEBUG: Fallback list fetch: Added '{metadata['subject']}' (ID: {metadata['id']}) for user {user_id}")
    
    if not messages_to_process and highest_history_id_in_fetch == 0:
        highest_history_id_in_fetch = get_latest_history_id_from_gmail_api(user_id=user_id) # <-- Pass user_id
        print(f"DEBUG: Fallback list fetch: No truly new unread messages, setting historyId to current API history: {highest_history_id_in_fetch} for user {user_id}")

    messages_to_process.sort(key=lambda x: (x['historyId'], x['id']))
    return messages_to_process, highest_history_id_in_fetch