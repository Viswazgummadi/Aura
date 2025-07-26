# Import the CRUD functions we want to use and the session management
from src.database import crud
from src.database.database import SessionLocal

# --- Public Tool Functions ---

def add_task(description: str) -> dict:
    """
    Adds a new task to the list by saving it to the database.

    Args:
        description: The description of the task.

    Returns:
        A dictionary representing the newly created task.
    """
    print(f"TOOL: add_task called with description: '{description}'")
    db = SessionLocal()
    try:
        # Call the CRUD function to create the task in the database
        new_task = crud.create_task(db=db, description=description)
        
        # We return a dictionary, as this is a more portable format than a class object.
        return {
            "id": new_task.id,
            "description": new_task.description,
            "status": new_task.status,
            "created_at": new_task.created_at.isoformat()
        }
    finally:
        db.close()

def list_tasks(status_filter: str = None) -> list[dict]:
    """
    Lists tasks from the database, optionally filtering by status.

    Args:
        status_filter: Optional. Either 'pending' or 'completed'.

    Returns:
        A list of task dictionaries.
    """
    print(f"TOOL: list_tasks called with filter: '{status_filter}'")
    db = SessionLocal()
    try:
        if status_filter:
            # Call the CRUD function to get tasks by status
            tasks_from_db = crud.get_tasks_by_status(db=db, status=status_filter)
        else:
            # Call the CRUD function to get all tasks
            tasks_from_db = crud.get_all_tasks(db=db)
        
        # Convert the list of Task objects into a list of dictionaries
        return [
            {
                "id": task.id,
                "description": task.description,
                "status": task.status,
                "created_at": task.created_at.isoformat()
            }
            for task in tasks_from_db
        ]
    finally:
        db.close()

def mark_task_complete(task_id: str) -> dict | None:
    """
    Marks a task as 'completed' in the database.

    Args:
        task_id: The ID of the task to mark as complete.

    Returns:
        The updated task dictionary, or None if the task was not found.
    """
    print(f"TOOL: mark_task_complete called with ID: '{task_id}'")
    db = SessionLocal()
    try:
        # Call the CRUD function to update the task status
        updated_task = crud.update_task_status(db=db, task_id=task_id, new_status="completed")
        
        if updated_task:
            return {
                "id": updated_task.id,
                "description": updated_task.description,
                "status": updated_task.status,
                "created_at": updated_task.created_at.isoformat()
            }
        # If the task was not found, return None
        return None
    finally:
        db.close()