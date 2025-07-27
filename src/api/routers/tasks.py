# src/api/routers/tasks.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# --- MODIFIED: We no longer need the crud layer here ---
from src.database.database import get_db
from src.database.models import TaskCreate, TaskResponse, TaskUpdate, User
from src.api.dependencies import get_current_user
# --- NEW: Import the tools which are now our source of truth ---
from src.agent.tools import tasks as tasks_tools

router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"]
)

@router.post("", response_model=TaskResponse, status_code=status.HTTP_2_CREATED)
def create_new_task(
    task: TaskCreate,
    current_user: User = Depends(get_current_user)
):
    """API endpoint to create a new task."""
    # This endpoint now calls the tool, passing the authenticated user's ID.
    return tasks_tools.create_task(
        user_id=current_user.id,
        description=task.description,
        priority=task.priority,
        due_date=task.due_date.isoformat() if task.due_date else None
    )

@router.get("", response_model=List[TaskResponse])
def get_all_user_tasks(
    current_user: User = Depends(get_current_user)
):
    """API endpoint to retrieve a list of all tasks."""
    return tasks_tools.get_all_tasks(user_id=current_user.id)

@router.put("/{task_id}", response_model=TaskResponse)
def update_a_task(
    task_id: str,
    task_update: TaskUpdate,
    current_user: User = Depends(get_current_user)
):
    """API endpoint to update a task's attributes."""
    # The tool function takes all possible arguments.
    # The Pydantic model ensures we only pass what the user provided.
    updated_task_dict = tasks_tools.update_task(
        user_id=current_user.id,
        task_id=task_id,
        description=task_update.description,
        status=task_update.status,
        priority=task_update.priority,
        due_date=task_update.due_date.isoformat() if task_update.due_date else None
    )
    if "error" in updated_task_dict:
        raise HTTPException(status_code=404, detail=updated_task_dict["error"])
    return updated_task_dict

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_a_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """API endpoint to delete a specific task."""
    result = tasks_tools.delete_task(user_id=current_user.id, task_id=task_id)
    if "Error" in result:
        raise HTTPException(status_code=404, detail=result)
    return