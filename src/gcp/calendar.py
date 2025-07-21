# In src/gcp/calendar.py
import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Permissions for all Google tools
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly"
]
TOKEN_PATH = "token.json"
CREDS_PATH = "credentials.json"

def get_calendar_service():
    """Authenticates with the Calendar API using the existing token.json."""
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, "w") as token:
                token.write(creds.to_json())
        else:
            raise Exception("Authentication required. Please run the `!auth` command.")
    return build('calendar', 'v3', credentials=creds)

def run_auth_flow():
    """
    Runs the local server authorization flow. This will print a URL for the user
    to open in their browser. After authorization, it creates token.json.
    """
    if not os.path.exists(CREDS_PATH):
        raise FileNotFoundError(f"CRITICAL: '{CREDS_PATH}' not found.")
    
    flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
    
    # This is the correct method for Desktop app credentials. It will print a URL
    # and wait for the user to authorize in their browser.
    creds = flow.run_local_server(port=0)
    
    # Save the new credentials after successful auth flow
    with open(TOKEN_PATH, "w") as token:
        token.write(creds.to_json())
    return creds

# ... (fetch_upcoming_events and update_event functions are correct and unchanged) ...
def fetch_upcoming_events(max_results=5) -> list:
    try:
        service = get_calendar_service()
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        events_result = service.events().list(
            calendarId="primary", timeMin=now, maxResults=max_results,
            singleEvents=True, orderBy="startTime"
        ).execute()
        return events_result.get("items", [])
    except Exception as e:
        print(f"An error occurred in fetch_upcoming_events: {e}")
        raise e

def update_event(event_id: str, summary: str, start_time_iso: str, end_time_iso: str, description: str, location: str) -> dict:
    try:
        service = get_calendar_service()
        event_body = {
            'summary': summary, 'location': location, 'description': description,
            'start': {'dateTime': start_time_iso, 'timeZone': 'UTC'},
            'end': {'dateTime': end_time_iso, 'timeZone': 'UTC'},
        }
        updated_event = service.events().update(
            calendarId='primary', eventId=event_id, body=event_body
        ).execute()
        return updated_event
    except HttpError as error:
        print(f'An HttpError occurred: {error}')
        return None