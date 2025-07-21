# In src/gcp/gmail.py
import base64
import os.path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# IMPORTANT: We define the scopes here too, matching calendar.py,
# to ensure we get a credential that can do everything.
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly"
]
TOKEN_PATH = "token.json"
CREDS_PATH = "credentials.json"

def get_gmail_service():
    """
    Authenticates with the Gmail API using the same token as the calendar.
    Returns a service object.
    """
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    
    # If creds are missing or invalid, the user needs to re-auth via another command first
    # (like !events or a future !auth command)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save the refreshed credentials
            with open(TOKEN_PATH, "w") as token:
                token.write(creds.to_json())
        else:
            # We can't trigger the auth flow from here directly without blocking.
            # We raise an error to be handled by the bot command.
            raise Exception("User not authenticated. Please run `!events` first to log in.")

    return build('gmail', 'v1', credentials=creds)

def fetch_unread_emails(max_results=5) -> list:
    """
    Fetches the subject and sender of the latest unread emails.
    """
    try:
        service = get_gmail_service()
        # Get the list of unread message IDs
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
        # If it's our custom auth error, re-raise it to be caught by the bot
        if "User not authenticated" in str(e):
            raise e
        return []