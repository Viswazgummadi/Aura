import datetime
from googleapiclient.errors import HttpError

from src.core.gcp_auth import build_google_service
from src.core.utils import to_rfc3339 # <-- NEW IMPORT

# --- Public Tool Functions for Calendar ---

def fetch_upcoming_events(user_id: int, max_results: int = 5) -> list:
    print(f"TOOL: fetch_upcoming_events called for user ID: {user_id}")
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    try:
        service = build_google_service('calendar', 'v3', user_id)
        time_min = to_rfc3339(now_utc)
        events_result = service.events().list(
            calendarId="primary",
            timeMin=time_min,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        return events_result.get("items", [])
    except HttpError as error:
        print(f"An HttpError occurred in fetch_upcoming_events for user {user_id}: {error}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred in fetch_upcoming_events for user {user_id}: {e}")
        raise

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
def update_calendar_event(
    user_id: int,
    event_id: str,
    summary: str = None,
    start_time_iso: str = None,
    end_time_iso: str = None,
    description: str = None,
    location: str = None
) -> dict | None:
    """
    Updates an existing calendar event. Only the provided fields will be changed.
    """
    print(f"TOOL: update_calendar_event called for user {user_id}, event {event_id}")
    try:
        service = build_google_service('calendar', 'v3', user_id=user_id)
        
        # First, get the existing event to ensure it exists and to preserve its other data
        event = service.events().get(calendarId='primary', eventId=event_id).execute()

        # Update fields only if they are provided in the call
        if summary:
            event['summary'] = summary
        if location:
            event['location'] = location
        if description:
            event['description'] = description
        if start_time_iso:
            event['start'] = {'dateTime': start_time_iso, 'timeZone': 'UTC'}
        if end_time_iso:
            event['end'] = {'dateTime': end_time_iso, 'timeZone': 'UTC'}

        updated_event = service.events().update(
            calendarId='primary',
            eventId=event['id'],
            body=event
        ).execute()
        
        print(f"Event updated for user {user_id}: {updated_event.get('htmlLink')}")
        return updated_event
    except HttpError as error:
        print(f'An HttpError occurred during event update for user {user_id}: {error}')
        raise error
    except Exception as e:
        print(f"An unexpected error occurred during event update for user {user_id}: {e}")
        raise e

def delete_calendar_event(user_id: int, event_id: str) -> bool:
    """
    Deletes a calendar event.
    """
    print(f"TOOL: delete_calendar_event called for user {user_id}, event {event_id}")
    try:
        service = build_google_service('calendar', 'v3', user_id=user_id)
        
        service.events().delete(
            calendarId='primary',
            eventId=event_id
        ).execute()
        
        print(f"Event {event_id} deleted successfully for user {user_id}.")
        return True
    except HttpError as error:
        # If the event is already deleted, Google sends a 410 Gone status. This is success.
        if error.resp.status == 410:
            print(f"Event {event_id} was already gone. Considering it deleted.")
            return True
        print(f'An HttpError occurred during event deletion for user {user_id}: {error}')
        raise error
    except Exception as e:
        print(f"An unexpected error occurred during event deletion for user {user_id}: {e}")
        raise e