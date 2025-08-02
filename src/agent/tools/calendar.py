# src/agent/tools/calendar.py

from langchain_core.tools import tool
from typing import List, Dict, Optional, Union
from googleapiclient.errors import HttpError
from src.core.gcp_auth import build_google_service
import datetime

@tool
def list_upcoming_events(max_results: int = 10, **kwargs) -> Union[List[Dict], Dict]:
    """
    Lists the user's upcoming Google Calendar events.
    Use this to check the user's schedule.
    """
    try:
        user_id = kwargs.get("user_id")
        if user_id is None:
            raise ValueError("list_upcoming_events tool was called without a user_id.")

        service = build_google_service('calendar', 'v3', user_id=user_id)
        events_result = service.events().list(
            calendarId="primary",
            timeMin=(datetime.datetime.now(datetime.timezone.utc)).isoformat(),
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        return events_result.get("items", [])
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}

@tool
def create_calendar_event(summary: str, start_time_iso: str, end_time_iso: str, description: Optional[str] = None, location: Optional[str] = None, **kwargs) -> Dict:
    """
    Creates a new event on the user's Google Calendar.
    `start_time_iso` and `end_time_iso` must be in 'YYYY-MM-DDTHH:MM:SSZ' format.
    """
    try:
        user_id = kwargs.get("user_id")
        if user_id is None:
            raise ValueError("create_calendar_event tool was called without a user_id.")

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
def update_calendar_event(event_id: str, summary: Optional[str] = None, start_time_iso: Optional[str] = None, end_time_iso: Optional[str] = None, description: Optional[str] = None, location: Optional[str] = None, **kwargs) -> Dict:
    """
    Updates an existing Google Calendar event. You must provide the event_id.
    Only include the fields you want to change.
    """
    try:
        user_id = kwargs.get("user_id")
        if user_id is None:
            raise ValueError("update_calendar_event tool was called without a user_id.")

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
def delete_calendar_event(event_id: str, **kwargs) -> Dict:
    """
    Deletes an event from the user's Google Calendar by its ID.
    """
    try:
        user_id = kwargs.get("user_id")
        if user_id is None:
            raise ValueError("delete_calendar_event tool was called without a user_id.")

        service = build_google_service('calendar', 'v3', user_id=user_id)
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return {"status": "success", "message": f"Event with ID '{event_id}' has been deleted."}
    except HttpError as e:
        if e.resp.status in [404, 410]: # Not Found or Gone
            return {"error": f"Event with ID '{event_id}' not found or already deleted."}
        return {"error": f"An API error occurred: {e}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}

__tools__ = [
    list_upcoming_events,
    create_calendar_event,
    update_calendar_event,
    delete_calendar_event
]