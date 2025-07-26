import datetime
from googleapiclient.errors import HttpError

from src.core.gcp_auth import build_google_service

# --- Public Tool Functions for Calendar ---

def fetch_upcoming_events(user_id: int, max_results: int = 5) -> list:
    print(f"TOOL: fetch_upcoming_events called for user ID: {user_id}")
    try:
        service = build_google_service('calendar', 'v3', user_id=user_id)
        
        # Ensure 'now' is explicitly timezone-aware UTC for the API call
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        
        events_result = service.events().list(
            calendarId="primary", 
            timeMin=now_utc.isoformat(), # Use ISO format string for API request
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
    start_time_iso: str, 
    end_time_iso: str, 
    description: str = None, 
    location: str = None
) -> dict | None:
    print(f"TOOL: create_new_event called for user ID: {user_id}, summary: '{summary}'")
    try:
        service = build_google_service('calendar', 'v3', user_id=user_id)

        # The API expects ISO 8601 with timezone info.
        # We explicitly set 'timeZone': 'UTC' for consistency.
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