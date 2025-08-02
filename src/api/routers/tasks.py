# src/api/routers/tasks.py

from fastapi import APIRouter, Depends, HTTPException, status, Query
from src.database.models import TaskCreate, TaskResponse, TaskUpdate, User
from src.api.dependencies import get_current_user
from src.agent.tools import tasks as tasks_tools
from typing import Optional, List
from sqlalchemy.orm import Session
from src.database import crud, database
router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_new_task(
    task: TaskCreate, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(database.get_db) # <-- Add the DB dependency
):
    """
    Creates a new task directly via the API.
    This endpoint communicates directly with the database layer.
    """
    # The 'task' variable is a Pydantic model (TaskCreate) from the request body.
    # The 'current_user' is our authenticated user object.
    # We pass both directly to the CRUD function.
    db_task = crud.create_task(db=db, task=task, user_id=current_user.id)
    return db_task

@router.get("", response_model=list[TaskResponse])
def get_all_user_tasks(
    status: Optional[str] = Query(None, description="Filter tasks by status (e.g., 'pending', 'completed')"),
    priority: Optional[str] = Query(None, description="Filter tasks by priority (e.g., 'high', 'medium', 'low')"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(database.get_db) # <-- Add the DB dependency
):
    """
    Get a list of all tasks for the current user.
    You can optionally filter the tasks by their status or priority.
    """
    # Call the CRUD function directly. This is much cleaner and more correct.
    tasks = crud.get_all_tasks(
        db=db, 
        user_id=current_user.id, 
        status=status, 
        priority=priority
    )
    return tasks

@router.post("/batch", response_model=List[TaskResponse], status_code=status.HTTP_201_CREATED)
def create_new_tasks_batch(tasks: List[TaskCreate], current_user: User = Depends(get_current_user)):
    """
    Creates multiple tasks for the current user in a single batch operation.
    """
    # The Pydantic model `List[TaskCreate]` has already validated the incoming list of tasks.
    # We need to convert this list of Pydantic models into a list of simple dictionaries
    # for the tool's invoke method.
    tasks_as_dicts = [task.model_dump(exclude_unset=True) for task in tasks]
    
    # Handle the due_date format conversion for each task in the list
    for task_dict in tasks_as_dicts:
        if 'due_date' in task_dict and task_dict['due_date']:
            task_dict['due_date'] = task_dict['due_date'].isoformat().replace('+00:00', 'Z')
            
    tool_input = {
        "user_id": current_user.id,
        "tasks": tasks_as_dicts
    }
    
    return tasks_tools.create_task_batch.invoke(tool_input)
@router.put("/{task_id}", response_model=TaskResponse)
def update_a_task(task_id: str, task_update: TaskUpdate, current_user: User = Depends(get_current_user)):
    tool_input = task_update.model_dump(exclude_unset=True)
    tool_input["user_id"] = current_user.id
    tool_input["task_id"] = task_id
    if tool_input.get("due_date"):
        tool_input["due_date"] = tool_input["due_date"].isoformat().replace('+00:00', 'Z')
        
    updated_task_dict = tasks_tools.update_task.invoke(tool_input)
    if "error" in updated_task_dict:
        raise HTTPException(status_code=404, detail=updated_task_dict["error"])
    return updated_task_dict

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_a_task(task_id: str, current_user: User = Depends(get_current_user)):
    result = tasks_tools.delete_task.invoke({"user_id": current_user.id, "task_id": task_id})
    if "error" in result:
        raise HTTPException(status_code=404, detail=result)
    return
@router.get("/{task_id}", response_model=TaskResponse)
def get_single_task(task_id: str, current_user: User = Depends(get_current_user)):
    """
    Get a single task by its unique ID.
    This endpoint will return the task along with its nested sub-tasks and linked notes.
    """
    tool_input = {"user_id": current_user.id, "task_id": task_id}
    
    # We need a tool to fetch a single task. Let's assume it's called `get_task_by_id`.
    task = tasks_tools.get_task_by_id.invoke(tool_input)

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    return task