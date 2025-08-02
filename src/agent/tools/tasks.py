# src/agent/tools/tasks.py

from langchain_core.tools import tool
from typing import List, Dict, Optional
import datetime
import uuid
from src.database import crud, database, models

@tool
def create_task(description: str, priority: Optional[str] = "medium", status: Optional[str] = "pending", due_date: Optional[str] = None, parent_id: Optional[str] = None, **kwargs) -> Dict:
    """
    Creates a new task for a user. Use this to add a new item to the user's to-do list.
    To create a sub-task, provide the `parent_id` of the parent task.
    You can optionally provide a priority ('low', 'medium', 'high'), a status ('pending', 'completed'), and a due_date (in 'YYYY-MM-DDTHH:MM:SSZ' format).
    """
    db = database.SessionLocal()
    try:
        user_id = kwargs.get("user_id")
        if user_id is None:
            raise ValueError("create_task tool was called without a user_id.")

        due_date_dt = datetime.datetime.fromisoformat(due_date.replace("Z", "+00:00")) if due_date else None
        task_create = models.TaskCreate(
            description=description,
            priority=priority,
            status=status,
            due_date=due_date_dt,
            parent_id=parent_id
        )
        db_task = crud.create_task(db=db, task=task_create, user_id=user_id)
        return models.TaskResponse.from_orm(db_task).model_dump()
    finally:
        db.close()

@tool
def create_task_batch(tasks: List[Dict], **kwargs) -> List[Dict]:
    """
    Creates multiple tasks for a user in a single operation.
    The `tasks` argument should be a list of dictionaries, where each dictionary
    represents a task and can contain 'description', 'priority', 'status', 'parent_id', etc.
    Use this to efficiently create multiple tasks at once.
    """
    db = database.SessionLocal()
    try:
        user_id = kwargs.get("user_id")
        if user_id is None:
            raise ValueError("create_task_batch tool was called without a user_id.")

        task_create_models = [models.TaskCreate(**task) for task in tasks]
        created_tasks = crud.create_task_batch(db, tasks=task_create_models, user_id=user_id)
        return [models.TaskResponse.from_orm(task).model_dump() for task in created_tasks]
    finally:
        db.close()

@tool
def get_all_tasks(status: Optional[str] = None, priority: Optional[str] = None, **kwargs) -> List[Dict]:
    """
    Retrieves a list of tasks for a user, with optional filters.
    Use this to see what is currently on the user's to-do list.
    You can filter by `status` (e.g., 'pending', 'completed') or by `priority` (e.g., 'high', 'medium', 'low').
    The tasks are intelligently sorted by status, due date, and priority.
    """
    db = database.SessionLocal()
    try:
        user_id = kwargs.get("user_id")
        if user_id is None:
            raise ValueError("get_all_tasks tool was called without a user_id.")

        tasks = crud.get_all_tasks(db, user_id=user_id, status=status, priority=priority)
        return [models.TaskResponse.from_orm(task).model_dump() for task in tasks]
    finally:
        db.close()

@tool
def get_task_by_id(task_id: str, **kwargs) -> Optional[Dict]:
    """
    Retrieves a single, specific task by its unique ID.
    Use this to get the full details of a task, including its sub-tasks and linked notes.
    Returns the task data as a dictionary if found, otherwise returns None.
    """
    db = database.SessionLocal()
    try:
        user_id = kwargs.get("user_id")
        if user_id is None:
            raise ValueError("get_task_by_id tool was called without a user_id.")

        task = crud.get_task_by_id(db, task_id=task_id, user_id=user_id)
        if task:
            return models.TaskResponse.from_orm(task).model_dump()
        return None
    finally:
        db.close()

@tool
def update_task(task_id: str, description: Optional[str] = None, status: Optional[str] = None, priority: Optional[str] = None, due_date: Optional[str] = None, **kwargs) -> Dict:
    """
    Updates a task's attributes. You must provide the task_id.
    Use this to change a task's description, mark it as 'completed', change its priority, or reschedule its due_date.
    """
    db = database.SessionLocal()
    try:
        user_id = kwargs.get("user_id")
        if user_id is None:
            raise ValueError("update_task tool was called without a user_id.")

        update_data = {}
        if description is not None:
            update_data['description'] = description
        if status is not None:
            update_data['status'] = status
        if priority is not None:
            update_data['priority'] = priority
        if due_date is not None:
            update_data['due_date'] = datetime.datetime.fromisoformat(due_date.replace("Z", "+00:00"))

        if not update_data:
            return {"error": "No update data provided."}

        task_update = models.TaskUpdate(**update_data)
        updated_task = crud.update_task(db, task_id=task_id, task_update=task_update, user_id=user_id)

        if not updated_task:
            return {"error": "Task not found."}
        return models.TaskResponse.from_orm(updated_task).model_dump()
    finally:
        db.close()


@tool
def delete_task(task_id: str, **kwargs) -> Dict:
    """
    Deletes a task by its ID. Use this to permanently remove a task from the user's list.
    Returns a success message or an error dictionary.
    """
    db = database.SessionLocal()
    try:
        user_id = kwargs.get("user_id")
        if user_id is None:
            raise ValueError("delete_task tool was called without a user_id.")

        deleted = crud.delete_task_by_id(db, task_id=task_id, user_id=user_id)
        if not deleted:
            return {"error": f"Task with ID '{task_id}' not found."}
        return {"status": "success", "message": f"Task with ID '{task_id}' has been deleted."}
    finally:
        db.close()

__tools__ = [
    create_task,
    create_task_batch,
    get_all_tasks,
    get_task_by_id,
    update_task,
    delete_task
]