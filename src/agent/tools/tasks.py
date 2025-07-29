# src/agent/tools/tasks.py

from langchain_core.tools import tool
from typing import List, Dict, Optional
import datetime
import uuid
from src.database import crud, database, models

@tool
def create_task(user_id: int, description: str, priority: Optional[str] = "medium", status: Optional[str] = "pending", due_date: Optional[str] = None, parent_id: Optional[str] = None) -> Dict: # <-- Add parent_id
    """
    Creates a new task for a user. Use this to add a new item to the user's to-do list.
    To create a sub-task, provide the `parent_id` of the parent task.
    You can optionally provide a priority, a status, and a due_date.
    You can optionally provide a priority ('low', 'medium', 'high'), a status ('pending', 'completed'), and a due_date (in 'YYYY-MM-DDTHH:MM:SSZ' format).
    """
    db = database.SessionLocal()
    try:
        due_date_dt = datetime.datetime.fromisoformat(due_date.replace("Z", "+00:00")) if due_date else None
        task_create = models.TaskCreate(
            description=description, 
            priority=priority, 
            status=status, 
            due_date=due_date_dt,
            parent_id=parent_id # <-- Add parent_id
        )
        db_task = crud.create_task(db=db, task=task_create, user_id=user_id)
        return models.TaskResponse.from_orm(db_task).model_dump()
    finally:
        db.close()

@tool
def get_all_tasks(user_id: int, status: Optional[str] = None, priority: Optional[str] = None) -> List[Dict]:
    """
    Retrieves a list of tasks for a user, with optional filters.
    Use this to see what is currently on the user's to-do list.
    You can filter by `status` (e.g., 'pending', 'completed') or by `priority` (e.g., 'high', 'medium', 'low').
    The tasks are intelligently sorted by status, due date, and priority.
    """
    db = database.SessionLocal()
    try:
        # Pass the filters down to the CRUD function
        tasks = crud.get_all_tasks(db, user_id=user_id, status=status, priority=priority)
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
        # --- THE FIX ---
        # 1. Build a dictionary of only the arguments that were provided (not None)
        update_data = {}
        if description is not None:
            update_data['description'] = description
        if status is not None:
            update_data['status'] = status
        if priority is not None:
            update_data['priority'] = priority
        if due_date is not None:
            update_data['due_date'] = datetime.datetime.fromisoformat(due_date.replace("Z", "+00:00"))
            
        # 2. If no data was provided, we can't do an update.
        if not update_data:
            return {"error": "No update data provided."}

        # 3. Create the Pydantic model from our clean dictionary
        task_update = models.TaskUpdate(**update_data)
        
        # 4. Call the CRUD function
        updated_task = crud.update_task(db, task_id=task_id, task_update=task_update, user_id=user_id)
        
        if not updated_task:
            return {"error": "Task not found."}
        return models.TaskResponse.from_orm(updated_task).model_dump()
    finally:
        db.close()


@tool
def delete_task(user_id: int, task_id: str) -> Dict: # <-- Change return type hint to Dict
    """
    Deletes a task by its ID. Use this to permanently remove a task from the user's list.
    Returns a success message or an error dictionary.
    """
    db = database.SessionLocal()
    try:
        deleted = crud.delete_task_by_id(db, task_id=task_id, user_id=user_id)
        if not deleted:
            # This is the standardized error format
            return {"error": f"Task with ID '{task_id}' not found."}
        # This is a structured success message
        return {"status": "success", "message": f"Task with ID '{task_id}' has been deleted."}
    finally:
        db.close()