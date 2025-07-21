# In src/gcp/gmail.py
import os.path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly"
]
TOKEN_PATH = "token.json"

def get_gmail_service():
    """
    Authenticates with the Gmail API using the shared token.json.
    """
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    
    if not creds or not creds.valid:
        # The main auth flow will handle refreshing, so we just raise an error if invalid.
        raise Exception("Authentication required. Please run the `!auth` command.")

    return build('gmail', 'v1', credentials=creds)

def fetch_unread_emails(max_results=5) -> list:
    """
    Fetches the subject and sender of the latest unread emails.
    """
    try:
        service = get_gmail_service()
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
            msg = service.users().messages().get(userId='me', id=message['id'], format='metadata').execute()
            headers = msg.get('payload', {}).get('headers', [])
            subject = next((i['value'] for i in headers if i['name'] == 'Subject'), 'No Subject')
            sender = next((i['value'] for i in headers if i['name'] == 'From'), 'Unknown Sender')
            email_data.append({'subject': subject, 'sender': sender})
            
        return email_data
    except Exception as e:
        print(f"An error occurred in fetch_unread_emails: {e}")
        raise e