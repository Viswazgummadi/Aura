# File: src/agent/tools/gmail.py

import base64
import email
from email import policy
import time
from datetime import datetime, timedelta, timezone
from googleapiclient.errors import HttpError

from src.core.gcp_auth import build_google_service
import gmail_history_tracker


def fetch_unread_emails(max_results=5) -> list:
    try:
        service = build_google_service('gmail', 'v1')
        
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
            
            email_data.append({'subject': subject, 'sender': sender})
            
        return email_data
    except Exception as e:
        print(f"An error occurred in fetch_unread_emails: {e}")
        raise e
    
def get_email_body(message_id: str) -> str | None:
    try:
        service = build_google_service('gmail', 'v1')
        
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
        print(f"An error occurred in get_email_body for message {message_id}: {e}")
        raise e

def mark_message_as_read(message_id: str):
    try:
        service = build_google_service('gmail', 'v1')
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        print(f"DEBUG: Message {message_id} marked as read.")
    except Exception as e:
        print(f"WARNING: Could not mark message {message_id} as read: {e}")

def get_latest_history_id_from_gmail_api() -> int:
    try:
        service = build_google_service('gmail', 'v1')
        profile = service.users().getProfile(userId='me').execute()
        return int(profile.get('historyId', 0))
    except Exception as e:
        print(f"ERROR: Could not fetch latest history ID from Gmail profile API: {e}")
        return 0 

def _fetch_messages_from_list_api(label_ids: list, max_results: int = 50) -> list:
    service = build_google_service('gmail', 'v1')
    results = service.users().messages().list(
        userId='me', 
        labelIds=label_ids, 
        maxResults=max_results
    ).execute()
    return results.get('messages', [])

def _get_message_metadata(message_id: str, service) -> dict | None:
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
            print(f"DEBUG: Message {message_id} not found (might be deleted). Skipping.")
            return None
        raise
    except Exception as e:
        print(f"ERROR: Failed to get metadata for message {message_id}: {e}")
        return None


def fetch_new_messages_for_processing_from_api(start_history_id: int | None = None) -> tuple[list, int]:
    service = build_google_service('gmail', 'v1')
    
    current_gmail_api_history_id = get_latest_history_id_from_gmail_api()
    messages_to_process_raw = []
    
    effective_start_history_id = start_history_id if start_history_id is not None else 0

    print(f"DEBUG: fetch_new_messages_for_processing_from_api: Current Gmail API history: {current_gmail_api_history_id}, Tracker's effective start: {effective_start_history_id}")

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
            
            # --- START OF THE DEFINITIVE FIX ---
            for history_record in history_list:
                print(f">>> [RAW_HISTORY_DEBUG] Processing history record: {history_record}")

                messages_in_record = []
                # Check for messages added directly
                if 'messagesAdded' in history_record:
                    # Extract the actual message objects
                    messages_in_record.extend([item['message'] for item in history_record['messagesAdded']])

                # Check for labels being added (like 'INBOX' or 'UNREAD')
                if 'labelsAdded' in history_record:
                    for label_event in history_record['labelsAdded']:
                        # We only care if the 'INBOX' label was added, signifying a new arrival
                        if 'INBOX' in label_event.get('labelIds', []):
                             messages_in_record.extend(label_event['messages'])

                # Now process all unique messages found in this history record
                processed_ids_in_record = set()
                for message_summary in messages_in_record:
                    msg_id = message_summary['id']
                    
                    # Avoid processing the same message twice within the same history event
                    if msg_id in processed_ids_in_record:
                        continue
                    processed_ids_in_record.add(msg_id)

                    # Final check: is the message actually new and not already processed by a previous run?
                    if not gmail_history_tracker.is_message_processed(msg_id):
                        metadata = _get_message_metadata(msg_id, service)
                        
                        print(f">>> [DEEPER_DEBUG] Evaluating message metadata: {metadata}")

                        if metadata and gmail_history_tracker.get_current_email_address() and \
                           metadata['delivered_to'] == gmail_history_tracker.get_current_email_address().lower():
                            
                            messages_to_process_raw.append(metadata)
                            print(f"SUCCESS: Found new mail '{metadata['subject']}' (ID: {msg_id}). Queued for notification.")
                        
                        else:
                            known_email = gmail_history_tracker.get_current_email_address()
                            if not metadata:
                                print(f">>> [DEEPER_DEBUG] SKIPPED message {msg_id} because metadata was None.")
                            else:
                                print(f">>> [DEEPER_DEBUG] SKIPPED message '{metadata.get('subject', 'N/A')}' because of email mismatch.")
                                print(f"    - Expected 'Delivered-To': '{known_email.lower() if known_email else 'Unknown'}'")
                                print(f"    -  Actual 'Delivered-To': '{metadata.get('delivered_to', 'Not Found')}'")
            # --- END OF THE DEFINITIVE FIX ---

            next_page_token = history_response.get('nextPageToken')
            if not next_page_token:
                break
            time.sleep(0.1) 

        messages_to_process_raw.sort(key=lambda x: (x['historyId'], x['id']))
        
        print(f"DEBUG: fetch_new_messages_for_processing_from_api: Total {len(messages_to_process_raw)} raw messages fetched via history API.")
        
        return messages_to_process_raw, current_gmail_api_history_id
    
    except HttpError as error:
        if error.resp.status == 404 and "startHistoryId" in str(error):
            print(f"WARNING: history.list 404 for startHistoryId {effective_start_history_id}. History too old or invalid. Performing full unread sync to re-establish base. Error: {error._get_reason()}")
            return _fetch_unread_and_get_history_id_fallback(service)
        raise
    except Exception as e:
        print(f"An unexpected error occurred in fetch_new_messages_for_processing_from_api: {e}")
        raise e

def _fetch_unread_and_get_history_id_fallback(service) -> tuple[list, int]:
    messages_to_process = []
    highest_history_id_in_fetch = 0

    print("DEBUG: Performing unread list sync as fallback.")
    unread_messages_list = _fetch_messages_from_list_api(label_ids=['INBOX', 'UNREAD'], max_results=50) 
    
    for msg_summary in unread_messages_list:
        metadata = _get_message_metadata(msg_summary['id'], service)
        if metadata and gmail_history_tracker.get_current_email_address() and \
           metadata['delivered_to'] == gmail_history_tracker.get_current_email_address().lower():
            if not gmail_history_tracker.is_message_processed(metadata['id']):
                messages_to_process.append(metadata)
                if metadata['historyId'] > highest_history_id_in_fetch:
                    highest_history_id_in_fetch = metadata['historyId']
                print(f"DEBUG: Fallback list fetch: Added '{metadata['subject']}' (ID: {metadata['id']})")
            else:
                print(f"DEBUG: Fallback list fetch: Skipping message {metadata['id']} ('{metadata['subject']}'): Already processed by tracker.")
    
    if not messages_to_process and highest_history_id_in_fetch == 0:
        highest_history_id_in_fetch = get_latest_history_id_from_gmail_api()
        print(f"DEBUG: Fallback list fetch: No truly new unread messages, setting historyId to current API history: {highest_history_id_in_fetch}")

    messages_to_process.sort(key=lambda x: (x['historyId'], x['id']))
    return messages_to_process, highest_history_id_in_fetch