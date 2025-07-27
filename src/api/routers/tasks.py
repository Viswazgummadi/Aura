from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from src.database import crud
from src.database.database import get_db
from src.database.models import TaskCreate, TaskResponse, User # <-- NEW IMPORT: User model
from src.api.dependencies import get_current_user # <-- NEW IMPORT: Our authentication dependency

router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"]
)

# Endpoint to retrieve all tasks (now secured and user-specific)
@router.get("", response_model=List[TaskResponse])
def get_all_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # <-- NEW: Requires authentication
):
    """
    Retrieve a list of all tasks for the authenticated user.
    """
    print(f"API: Getting tasks for user ID: {current_user.id}")
    # Pass current_user.id to the CRUD function
    tasks = crud.get_all_tasks(db, user_id=current_user.id)
    return tasks

# Endpoint to create a new task (now secured and user-specific)
@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # <-- NEW: Requires authentication
):
    """
    Create a new task for the authenticated user.
    """
    print(f"API: Received request to create task for user {current_user.id}: {task.description}")
    # Pass current_user.id to the CRUD function
    db_task = crud.create_task(db=db, description=task.description, user_id=current_user.id)
    return db_task

# Endpoint to mark a task as complete (now secured and user-specific)
@router.put("/{task_id}/complete", response_model=TaskResponse)
def complete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # <-- NEW: Requires authentication
):
    """
    Mark an existing task for the authenticated user as 'completed'.
    """
    print(f"API: Received request to complete task {task_id} for user ID: {current_user.id}")
    
    # Pass current_user.id to the CRUD function
    updated_task = crud.update_task_status(db=db, task_id=task_id, user_id=current_user.id, new_status="completed")
    
    if not updated_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID '{task_id}' not found for user {current_user.id}." # More specific error message
        )
    return updated_task
@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an existing task for the authenticated user.
    """
    print(f"API: Received request to delete task {task_id} for user ID: {current_user.id}")
    
    # Call the new CRUD function
    deleted = crud.delete_task_by_id(db=db, task_id=task_id, user_id=current_user.id)
    
    # If the delete operation returned False, it means the task was not found
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID '{task_id}' not found for this user."
        )
    
    # If successful, FastAPI will automatically return a 204 No Content response
    return