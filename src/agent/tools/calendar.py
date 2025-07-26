import datetime
from googleapiclient.errors import HttpError

# Import the centralized function to build a Google service
from src.core.gcp_auth import build_google_service

# --- Public Tool Functions for Calendar ---

def fetch_upcoming_events(user_id: int, max_results: int = 5) -> list: # <-- NEW: user_id argument
    """
    Fetches upcoming events from the user's primary calendar.
    
    Args:
        user_id (int): The ID of the AIBuddies user whose calendar to access.
        max_results (int): The maximum number of events to retrieve.

    Returns:
        list: A list of event dictionaries.
    """
    print(f"TOOL: fetch_upcoming_events called for user ID: {user_id}")
    try:
        # Pass the user_id to build_google_service
        service = build_google_service('calendar', 'v3', user_id=user_id)
        
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        events_result = service.events().list(
            calendarId="primary", timeMin=now, maxResults=max_results,
            singleEvents=True, orderBy="startTime"
        ).execute()
        return events_result.get("items", [])
    except Exception as e:
        print(f"An error occurred in fetch_upcoming_events for user {user_id}: {e}")
        raise e

def create_new_event(
    user_id: int, # <-- NEW: user_id argument
    summary: str, 
    start_time_iso: str, 
    end_time_iso: str, 
    description: str = None, 
    location: str = None
) -> dict | None:
    """
    Creates a new event in the user's primary calendar.
    
    Args:
        user_id (int): The ID of the AIBuddies user whose calendar to access.
        summary (str): The title of the event.
        start_time_iso (str): Start time in ISO 8601 format (e.g., 'YYYY-MM-DDTHH:MM:SSZ').
        end_time_iso (str): End time in ISO 8601 format.
        description (str, optional): Description of the event.
        location (str, optional): Location of the event.

    Returns:
        dict | None: The newly created event dictionary, or None if creation failed.
    """
    print(f"TOOL: create_new_event called for user ID: {user_id}, summary: '{summary}'")
    try:
        # Pass the user_id to build_google_service
        service = build_google_service('calendar', 'v3', user_id=user_id)

        event_body = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {'dateTime': start_time_iso, 'timeZone': 'UTC'}, # Assume UTC for simplicity from original code
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