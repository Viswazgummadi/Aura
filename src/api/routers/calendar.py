from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import datetime

from src.database.database import get_db
from src.database.models import CalendarEventCreate, CalendarEventResponse, User
from src.api.dependencies import get_current_user
from src.agent.tools import calendar as calendar_tool

router = APIRouter(
    prefix="/calendar",
    tags=["Calendar"]
)

@router.get("/events", response_model=List[CalendarEventResponse])
def get_upcoming_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    max_results: int = 5
):
    """
    Retrieve a list of upcoming calendar events for the authenticated user.
    """
    print(f"API: Fetching upcoming events for user ID: {current_user.id}")
    try:
        events = calendar_tool.fetch_upcoming_events(user_id=current_user.id, max_results=max_results)
        
        response_events = []
        for event in events:
            # **CRITICAL FIX IS HERE:**
            # Handle both timed events (with 'dateTime') and all-day events (with 'date').
            # Use .get('dateTime') and fall back to .get('date') if it's missing.
            start_time = event.get('start', {}).get('dateTime', event.get('start', {}).get('date'))
            end_time = event.get('end', {}).get('dateTime', event.get('end', {}).get('date'))

            # Basic check to prevent validation error if an event is malformed
            if not start_time or not end_time:
                print(f"WARN: Skipping event with malformed start/end time: {event.get('id')}")
                continue

            response_events.append(
                CalendarEventResponse(
                    id=event.get('id'),
                    summary=event.get('summary', 'No Title'), # Add fallback for summary
                    start_time_iso=start_time,
                    end_time_iso=end_time,
                    description=event.get('description'),
                    location=event.get('location'),
                    html_link=event.get('htmlLink')
                )
            )
        return response_events
        
    except Exception as e:
        # It's good practice to log the actual exception for debugging
        print(f"ERROR in get_upcoming_events: {type(e).__name__} - {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch calendar events: {e}"
        )

@router.post("/events", response_model=CalendarEventResponse, status_code=status.HTTP_201_CREATED)
def create_calendar_event(
    event_data: CalendarEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new calendar event for the authenticated user.
    """
    print(f"API: Creating calendar event for user ID: {current_user.id}, summary: '{event_data.summary}'")
    try:
        new_event = calendar_tool.create_new_event(
            user_id=current_user.id,
            summary=event_data.summary,
            start_time_iso=event_data.start_time_iso,
            end_time_iso=event_data.end_time_iso,
            description=event_data.description,
            location=event_data.location
        )
        if not new_event:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create calendar event (unknown reason)."
            )
        
        # This part also needs the same fallback logic to be fully robust
        start_time = new_event.get('start', {}).get('dateTime', new_event.get('start', {}).get('date'))
        end_time = new_event.get('end', {}).get('dateTime', new_event.get('end', {}).get('date'))

        return CalendarEventResponse(
            id=new_event.get('id'),
            summary=new_event.get('summary'),
            start_time_iso=start_time,
            end_time_iso=end_time,
            description=new_event.get('description'),
            location=new_event.get('location'),
            html_link=new_event.get('htmlLink')
        )
    except Exception as e:
        print(f"ERROR in create_calendar_event: {type(e).__name__} - {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create calendar event: {e}"
        )