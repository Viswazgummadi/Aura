# src/agent/tools/calendar.py

from langchain_core.tools import tool
from typing import List, Dict, Optional, Union
from googleapiclient.errors import HttpError
from src.core.gcp_auth import build_google_service
import datetime

@tool
def list_upcoming_events(user_id: int, max_results: int = 10) -> Union[List[Dict], Dict]:
    """
    Lists the user's upcoming Google Calendar events.
    Use this to check the user's schedule.
    """
    try:
        service = build_google_service('calendar', 'v3', user_id)
        events_result = service.events().list(
            calendarId="primary",
            timeMin=(datetime.datetime.now(datetime.timezone.utc)).isoformat(),
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        return events_result.get("items", [])
    except Exception as e:
        # <-- CHANGED: Return a dictionary directly, not a list containing a dictionary.
        return {"error": f"An unexpected error occurred: {e}"}

@tool
def create_calendar_event(user_id: int, summary: str, start_time_iso: str, end_time_iso: str, description: Optional[str] = None, location: Optional[str] = None) -> Dict:
    """
    Creates a new event on the user's Google Calendar.
    `start_time_iso` and `end_time_iso` must be in 'YYYY-MM-DDTHH:MM:SSZ' format.
    """
    # This tool was already perfectly structured. No changes needed.
    try:
        service = build_google_service('calendar', 'v3', user_id=user_id)
        event_body = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {'dateTime': start_time_iso, 'timeZone': 'UTC'},
            'end': {'dateTime': end_time_iso, 'timeZone': 'UTC'},
        }
        new_event = service.events().insert(calendarId='primary', body=event_body).execute()
        return new_event
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}

@tool
def update_calendar_event(user_id: int, event_id: str, summary: str = None, start_time_iso: str = None, end_time_iso: str = None, description: str = None, location: str = None) -> Dict:
    """
    Updates an existing Google Calendar event. You must provide the event_id.
    Only include the fields you want to change.
    """
    # This tool was already perfectly structured. No changes needed.
    try:
        service = build_google_service('calendar', 'v3', user_id=user_id)
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        if summary: event['summary'] = summary
        if location: event['location'] = location
        if description: event['description'] = description
        if start_time_iso: event['start'] = {'dateTime': start_time_iso, 'timeZone': 'UTC'}
        if end_time_iso: event['end'] = {'dateTime': end_time_iso, 'timeZone': 'UTC'}
        updated_event = service.events().update(calendarId='primary', eventId=event['id'], body=event).execute()
        return updated_event
    except HttpError as e:
        if e.resp.status == 404:
            return {"error": f"Event with ID '{event_id}' not found."}
        return {"error": f"An API error occurred: {e}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}

@tool
def delete_calendar_event(user_id: int, event_id: str) -> Dict:
    """
    Deletes an event from the user's Google Calendar by its ID.
    """
    try:
        service = build_google_service('calendar', 'v3', user_id=user_id)
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        # <-- CHANGED: Return a structured success dictionary.
        return {"status": "success", "message": f"Event with ID '{event_id}' has been deleted."}
    except HttpError as e:
        # <-- CHANGED: Return a structured error dictionary.
        if e.resp.status in [404, 410]: # Not Found or Gone
            return {"error": f"Event with ID '{event_id}' not found or already deleted."}
        return {"error": f"An API error occurred: {e}"}
    except Exception as e:
        # <-- CHANGED: Return a structured error dictionary.
        return {"error": f"An unexpected error occurred: {e}"}
    
