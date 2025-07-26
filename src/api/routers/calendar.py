from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import datetime

from src.database.database import get_db
from src.database.models import CalendarEventCreate, CalendarEventResponse, User # <-- Import new schemas and User model
from src.api.dependencies import get_current_user # Our authentication dependency
from src.agent.tools import calendar as calendar_tool # Our refactored calendar tool

router = APIRouter(
    prefix="/calendar",
    tags=["Calendar"]
)

@router.get("/events", response_model=List[CalendarEventResponse])
def get_upcoming_events(
    db: Session = Depends(get_db), # Not directly used but good practice for dependency chain
    current_user: User = Depends(get_current_user), # Requires authentication
    max_results: int = 5
):
    """
    Retrieve a list of upcoming calendar events for the authenticated user.
    """
    print(f"API: Fetching upcoming events for user ID: {current_user.id}")
    try:
        # Call the refactored calendar tool with user_id
        events = calendar_tool.fetch_upcoming_events(user_id=current_user.id, max_results=max_results)
        # Convert to Pydantic model for response validation
        # The tool returns Google's dicts, so we map them to our Pydantic model
        return [
            CalendarEventResponse(
                id=event.get('id'),
                summary=event.get('summary'),
                start_time_iso=event.get('start', {}).get('dateTime'),
                end_time_iso=event.get('end', {}).get('dateTime'),
                description=event.get('description'),
                location=event.get('location'),
                html_link=event.get('htmlLink')
            ) for event in events
        ]
    except Exception as e:
        # Catch potential Google API errors (e.g., credentials expired)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch calendar events: {e}"
        )

@router.post("/events", response_model=CalendarEventResponse, status_code=status.HTTP_201_CREATED)
def create_calendar_event(
    event_data: CalendarEventCreate,
    db: Session = Depends(get_db), # Not directly used but good practice
    current_user: User = Depends(get_current_user) # Requires authentication
):
    """
    Create a new calendar event for the authenticated user.
    """
    print(f"API: Creating calendar event for user ID: {current_user.id}, summary: '{event_data.summary}'")
    try:
        # Call the refactored calendar tool with user_id
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
        # Convert to Pydantic model for response validation
        return CalendarEventResponse(
            id=new_event.get('id'),
            summary=new_event.get('summary'),
            start_time_iso=new_event.get('start', {}).get('dateTime'),
            end_time_iso=new_event.get('end', {}).get('dateTime'),
            description=new_event.get('description'),
            location=new_event.get('location'),
            html_link=new_event.get('htmlLink')
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create calendar event: {e}"
        )