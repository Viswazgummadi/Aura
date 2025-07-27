# src/agent/tools/tasks.py

from langchain_core.tools import tool
from typing import List, Dict, Optional
import datetime
import uuid
from src.database import crud, database, models

@tool
def create_task(user_id: int, description: str, priority: Optional[str] = "medium", due_date: Optional[str] = None) -> Dict:
    """
    Creates a new task for a user. Use this to add a new item to the user's to-do list.
    You can optionally provide a priority ('low', 'medium', 'high') and a due_date (in 'YYYY-MM-DDTHH:MM:SSZ' format).
    """
    db = database.SessionLocal()
    try:
        # Pydantic will handle parsing the ISO string to a datetime object
        due_date_dt = datetime.datetime.fromisoformat(due_date.replace("Z", "+00:00")) if due_date else None
        task_create = models.TaskCreate(description=description, priority=priority, due_date=due_date_dt)
        db_task = crud.create_task(db=db, task=task_create, user_id=user_id)
        # Use from_orm (or model_validate in Pydantic v2) to safely convert the SQLAlchemy object
        return models.TaskResponse.from_orm(db_task).model_dump()
    finally:
        db.close()

@tool
def get_all_tasks(user_id: int) -> List[Dict]:
    """
    Retrieves a list of all tasks for a user. Use this to see what is currently on the user's to-do list.
    The tasks are intelligently sorted by status, due date, and priority.
    """
    db = database.SessionLocal()
    try:
        tasks = crud.get_all_tasks(db, user_id=user_id)
        return [models.TaskResponse.from_orm(task).model_dump() for task in tasks]
    finally:
        db.close()

@tool
def update_task(user_id: int, task_id: str, description: Optional[str] = None, status: Optional[str] = None, priority: Optional[str] = None, due_date: Optional[str] = None) -> Dict:
    """
    Updates a task's attributes. You must provide the task_id.
    Use this to change a task's description, mark it as 'completed', change its priority, or reschedule its due_date.
    """
    db = database.SessionLocal()
    try:
        due_date_dt = datetime.datetime.fromisoformat(due_date.replace("Z", "+00:00")) if due_date else None
        task_update = models.TaskUpdate(description=description, status=status, priority=priority, due_date=due_date_dt)
        # Use exclude_unset=True so we only update provided fields
        updated_task = crud.update_task(db, task_id=task_id, task_update=task_update, user_id=user_id)
        if not updated_task:
            return {"error": "Task not found."}
        return models.TaskResponse.from_orm(updated_task).model_dump()
    finally:
        db.close()

@tool
def delete_task(user_id: int, task_id: str) -> str:
    """
    Deletes a task by its ID. Use this to permanently remove a task from the user's list.
    """
    db = database.SessionLocal()
    try:
        deleted = crud.delete_task_by_id(db, task_id=task_id, user_id=user_id)
        if not deleted:
            return f"Error: Task with ID '{task_id}' not found."
        return f"Success: Task with ID '{task_id}' has been deleted."
    finally:
        db.close()