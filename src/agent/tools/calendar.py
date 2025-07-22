# File: src/gcp/calendar.py

import datetime
from googleapiclient.errors import HttpError

# Import the centralized function to build a Google service
from src.core.gcp_auth import build_google_service

# This file now only contains functions directly related to the Calendar API.
# All authentication logic has been moved.

def fetch_upcoming_events(max_results=5) -> list:
    """Fetches upcoming events from the user's primary calendar."""
    try:
        # 1. Get an authorized calendar service object
        service = build_google_service('calendar', 'v3')
        
        # 2. Call the Calendar API
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        events_result = service.events().list(
            calendarId="primary", timeMin=now, maxResults=max_results,
            singleEvents=True, orderBy="startTime"
        ).execute()
        return events_result.get("items", [])
    except Exception as e:
        # Re-raise the exception so the command in the cog can handle it
        print(f"An error occurred in fetch_upcoming_events: {e}")
        raise e

def update_event(event_id: str, summary: str, start_time_iso: str, end_time_iso: str, description: str, location: str) -> dict | None:
    """Updates an existing event in the user's primary calendar."""
    try:
        # 1. Get an authorized calendar service object
        service = build_google_service('calendar', 'v3')

        # 2. Define the event body
        event_body = {
            'summary': summary, 
            'location': location, 
            'description': description,
            'start': {'dateTime': start_time_iso, 'timeZone': 'UTC'},
            'end': {'dateTime': end_time_iso, 'timeZone': 'UTC'},
        }

        # 3. Call the Calendar API to update the event
        updated_event = service.events().update(
            calendarId='primary', eventId=event_id, body=event_body
        ).execute()
        return updated_event
    except HttpError as error:
        # Re-raise the exception for the UI modal to handle
        print(f'An HttpError occurred during event update: {error}')
        raise error
    except Exception as e:
        print(f"An unexpected error occurred during event update: {e}")
        raise e