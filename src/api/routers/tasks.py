# src/api/routers/tasks.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from src.database import crud
from src.database.database import get_db
# Make sure to import the new TaskUpdate Pydantic model
from src.database.models import TaskCreate, TaskResponse, TaskUpdate, User
from src.api.dependencies import get_current_user

router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"]
)

@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_new_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new task for the authenticated user.
    You can optionally provide a `priority` ("low", "medium", "high")
    and a `due_date` (in ISO 8601 format).
    """
    return crud.create_task(db=db, task=task, user_id=current_user.id)

@router.get("", response_model=List[TaskResponse])
def get_all_user_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve a list of all tasks for the authenticated user.
    The tasks are intelligently sorted by status, due date, and priority.
    """
    return crud.get_all_tasks(db, user_id=current_user.id)

@router.put("/{task_id}", response_model=TaskResponse)
def update_a_task(
    task_id: str,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a task's attributes. You can update its description,
    status (e.g., to "completed"), priority, or due_date.
    Only include the fields you want to change in the request body.
    """
    updated_task = crud.update_task(db=db, task_id=task_id, task_update=task_update, user_id=current_user.id)
    if not updated_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated_task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_a_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Permanently delete a specific task by its ID.
    """
    deleted = crud.delete_task_by_id(db=db, task_id=task_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    # On successful deletion, return a 204 status code with no content.
    return