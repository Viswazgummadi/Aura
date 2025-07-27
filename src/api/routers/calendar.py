# src/api/routers/calendar.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from src.database.models import CalendarEventCreate, CalendarEventResponse, User, CalendarEventUpdate
from src.api.dependencies import get_current_user
from src.agent.tools import calendar as calendar_tools

router = APIRouter(
    prefix="/calendar",
    tags=["Calendar"]
)

@router.get("/events", response_model=List[CalendarEventResponse])
def get_upcoming_events(current_user: User = Depends(get_current_user), max_results: int = 10):
    events = calendar_tools.list_upcoming_events.invoke({
        "user_id": current_user.id, "max_results": max_results
    })
    if isinstance(events, list) and events and "error" in events[0]:
        raise HTTPException(status_code=500, detail=events[0]["error"])
    return events

@router.post("/events", response_model=CalendarEventResponse, status_code=status.HTTP_201_CREATED)
def create_calendar_event(event_data: CalendarEventCreate, current_user: User = Depends(get_current_user)):
    event = calendar_tools.create_calendar_event.invoke({
        "user_id": current_user.id,
        "summary": event_data.summary,
        "start_time_iso": event_data.start_time_iso,
        "end_time_iso": event_data.end_time_iso,
        "description": event_data.description,
        "location": event_data.location
    })
    if "error" in event:
        raise HTTPException(status_code=500, detail=event["error"])
    return event

@router.put("/events/{event_id}", response_model=CalendarEventResponse)
def update_event(event_id: str, event_data: CalendarEventUpdate, current_user: User = Depends(get_current_user)):
    tool_input = event_data.model_dump(exclude_unset=True)
    tool_input["user_id"] = current_user.id
    tool_input["event_id"] = event_id
    updated_event = calendar_tools.update_calendar_event.invoke(tool_input)
    if "error" in updated_event:
        if "not found" in updated_event["error"].lower():
            raise HTTPException(status_code=404, detail=updated_event["error"])
        raise HTTPException(status_code=500, detail=updated_event["error"])
    return updated_event

@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: str, current_user: User = Depends(get_current_user)):
    result = calendar_tools.delete_calendar_event.invoke({
        "user_id": current_user.id, "event_id": event_id
    })
    if "Error" in result:
        raise HTTPException(status_code=404, detail=result)
    return