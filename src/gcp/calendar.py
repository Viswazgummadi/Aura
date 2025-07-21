# In src/gcp/calendar.py
import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- STEP 1: PERMISSION CHANGE ---
# The scope is now for read/write access.
# Add the GMAIL scope to the list
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly"
]
TOKEN_PATH = "token.json"
CREDS_PATH = "credentials.json"

# (get_calendar_service and run_auth_flow are unchanged)
def get_calendar_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = run_auth_flow()
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)

def run_auth_flow():
    if not os.path.exists(CREDS_PATH):
        raise FileNotFoundError(f"CRITICAL: '{CREDS_PATH}' not found.")
    flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
    creds = flow.run_local_server(port=0)
    return creds

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
        return []

# --- STEP 2: NEW UPDATE FUNCTION ---
def update_event(event_id: str, summary: str, start_time_iso: str, end_time_iso: str, description: str, location: str) -> dict:
    """
    Updates an existing event in the user's primary calendar.
    """
    try:
        service = get_calendar_service()

        # Construct the body of the event with the new details.
        event_body = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time_iso,
                'timeZone': 'UTC', # Use UTC for consistency
            },
            'end': {
                'dateTime': end_time_iso,
                'timeZone': 'UTC',
            },
        }

        updated_event = service.events().update(
            calendarId='primary',
            eventId=event_id,
            body=event_body
        ).execute()

        return updated_event
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None