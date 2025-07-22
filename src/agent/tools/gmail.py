# File: src/gcp/gmail.py

from googleapiclient.errors import HttpError

# Import the centralized function to build a Google service
from src.core.gcp_auth import build_google_service

# This file now only contains functions directly related to the Gmail API.

def fetch_unread_emails(max_results=5) -> list:
    """
    Fetches the subject and sender of the latest unread emails.
    """
    try:
        # 1. Get an authorized Gmail service object
        service = build_google_service('gmail', 'v1')
        
        # 2. Call the Gmail API to get a list of unread message IDs
        results = service.users().messages().list(
            userId='me', 
            labelIds=['INBOX', 'UNREAD'], 
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        email_data = []

        if not messages:
            return []

        # 3. For each message ID, get the actual message content (metadata)
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
        # Re-raise the exception so the command in the cog can handle it
        print(f"An error occurred in fetch_unread_emails: {e}")
        raise e