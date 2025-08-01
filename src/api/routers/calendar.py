# src/api/routers/calendar.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from src.database.models import CalendarEventCreate, CalendarEventDeleteResponse,CalendarEventResponse, User, CalendarEventUpdate
from src.api.dependencies import get_current_user
from src.agent.tools import calendar as calendar_tools

router = APIRouter(
    prefix="/calendar",
    tags=["Calendar"]
)

@router.get("/events", response_model=List[CalendarEventResponse])
def get_upcoming_events(current_user: User = Depends(get_current_user), max_results: int = 10):
    events_from_tool = calendar_tools.list_upcoming_events.invoke({
        "user_id": current_user.id, "max_results": max_results
    })
    if isinstance(events_from_tool, list) and events_from_tool and "error" in events_from_tool[0]:
        raise HTTPException(status_code=500, detail=events_from_tool[0]["error"])
    
    # --- THIS IS THE FIX: Manually map the Google response to our Pydantic model ---
    response_events = []
    for event in events_from_tool:
        start_time = event.get('start', {}).get('dateTime', event.get('start', {}).get('date'))
        end_time = event.get('end', {}).get('dateTime', event.get('end', {}).get('date'))
        response_events.append(
            CalendarEventResponse(
                id=event.get('id'),
                summary=event.get('summary'),
                start_time_iso=start_time,
                end_time_iso=end_time,
                description=event.get('description'),
                location=event.get('location'),
                html_link=event.get('htmlLink')
            )
        )
    return response_events

@router.delete("/events/delete", response_model=CalendarEventDeleteResponse, status_code=status.HTTP_201_CREATED)
def delete_calendar_event(event_id: str, current_user: User = Depends(get_current_user)):
    event_from_tool = calendar_tools.delete_calendar_event.invoke({
        "user_id": current_user.id, "event_id": event_id
    })
    if "error" in event_from_tool:
        raise HTTPException(status_code=500, detail=event_from_tool["error"])
    return CalendarEventDeleteResponse(
    status=event_from_tool["status"],
    message=event_from_tool["message"]
)


    
    
    
@router.post("/events", response_model=CalendarEventResponse, status_code=status.HTTP_201_CREATED)
def create_calendar_event(event_data: CalendarEventCreate, current_user: User = Depends(get_current_user)):
    event_from_tool = calendar_tools.create_calendar_event.invoke({
        "user_id": current_user.id,
        "summary": event_data.summary,
        "start_time_iso": event_data.start_time_iso,
        "end_time_iso": event_data.end_time_iso,
        "description": event_data.description,
        "location": event_data.location
    })
    if "error" in event_from_tool:
        raise HTTPException(status_code=500, detail=event_from_tool["error"])
    
    # --- THIS IS THE FIX: Manually map the Google response to our Pydantic model ---
    start_time = event_from_tool.get('start', {}).get('dateTime', event_from_tool.get('start', {}).get('date'))
    end_time = event_from_tool.get('end', {}).get('dateTime', event_from_tool.get('end', {}).get('date'))
    return CalendarEventResponse(
        id=event_from_tool.get('id'),
        summary=event_from_tool.get('summary'),
        start_time_iso=start_time,
        end_time_iso=end_time,
        description=event_from_tool.get('description'),
        location=event_from_tool.get('location'),
        html_link=event_from_tool.get('htmlLink')
    )
# The update and delete endpoints should also have this mapping if they return a full event
@router.put("/events/{event_id}", response_model=CalendarEventResponse)
def update_event(event_id: str, event_data: CalendarEventUpdate, current_user: User = Depends(get_current_user)):
    tool_input = event_data.model_dump(exclude_unset=True)
    tool_input["user_id"] = current_user.id
    tool_input["event_id"] = event_id
    updated_event_from_tool = calendar_tools.update_calendar_event.invoke(tool_input)
    if "error" in updated_event_from_tool:
        if "not found" in updated_event_from_tool["error"].lower():
            raise HTTPException(status_code=404, detail=updated_event_from_tool["error"])
        raise HTTPException(status_code=500, detail=updated_event_from_tool["error"])
    
    # --- ADD THE MAPPING HERE AS WELL ---
    start_time = updated_event_from_tool.get('start', {}).get('dateTime', updated_event_from_tool.get('start', {}).get('date'))
    end_time = updated_event_from_tool.get('end', {}).get('dateTime', updated_event_from_tool.get('end', {}).get('date'))
    return CalendarEventResponse(
        id=updated_event_from_tool.get('id'),
        summary=updated_event_from_tool.get('summary'),
        start_time_iso=start_time,
        end_time_iso=end_time,
        description=updated_event_from_tool.get('description'),
        location=updated_event_from_tool.get('location'),
        html_link=updated_event_from_tool.get('htmlLink')
    )