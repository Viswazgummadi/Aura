import datetime
from googleapiclient.errors import HttpError

from src.core.gcp_auth import build_google_service
from src.core.utils import to_rfc3339 # <-- NEW IMPORT

# --- Public Tool Functions for Calendar ---

def fetch_upcoming_events(user_id: int, max_results: int = 5) -> list:
    print(f"TOOL: fetch_upcoming_events called for user ID: {user_id}")
    print(f"DEBUG: now_utc = {now_utc}, tzinfo = {now_utc.tzinfo}, aware = {now_utc.tzinfo is not None}")
    try:
        service = build_google_service('calendar', 'v3', user_id=user_id)
        
        # Get current time as timezone-aware UTC datetime
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        
        # Convert to RFC 3339 string for the API call
        time_min_rfc3339 = to_rfc3339(now_utc) # <-- FIX: Use new utility function
        
        events_result = service.events().list(
            calendarId="primary", 
            timeMin=time_min_rfc3339, # <-- Use RFC 3339 string
            maxResults=max_results,
            singleEvents=True, 
            orderBy="startTime"
        ).execute()
        return events_result.get("items", [])
    except HttpError as error:
        print(f"An HttpError occurred in fetch_upcoming_events for user {user_id}: {error}")
        raise error
    except Exception as e:
        print(f"An unexpected error occurred in fetch_upcoming_events for user {user_id}: {e}")
        raise e

def create_new_event(
    user_id: int,
    summary: str, 
    start_time_iso: str, # This should already be RFC 3339 from frontend/Pydantic
    end_time_iso: str,   # This should already be RFC 3339 from frontend/Pydantic
    description: str = None, 
    location: str = None
) -> dict | None:
    print(f"TOOL: create_new_event called for user ID: {user_id}, summary: '{summary}'")
    try:
        service = build_google_service('calendar', 'v3', user_id=user_id)

        # Ensure that start_time_iso and end_time_iso are indeed RFC 3339 compliant strings
        # If your frontend sends "YYYY-MM-DDTHH:MM:SS" (naive), you might need to
        # parse them to datetime objects, make them aware, and then to_rfc3339.
        # For this example, we assume the input ISO strings are already correct.
        event_body = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {'dateTime': start_time_iso, 'timeZone': 'UTC'},
            'end': {'dateTime': end_time_iso, 'timeZone': 'UTC'},
        }

        new_event = service.events().insert(
            calendarId='primary', 
            body=event_body
        ).execute()
        
        print(f"Event created for user {user_id}: {new_event.get('htmlLink')}")
        return new_event
    except HttpError as error:
        print(f'An HttpError occurred during event creation for user {user_id}: {error}')
        raise error
    except Exception as e:
        print(f"An unexpected error occurred during event creation for user {user_id}: {e}")
        raise e