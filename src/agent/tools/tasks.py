# File: src/agent/tools/tasks.py

import json
import os
import uuid
from datetime import datetime

# Define the path for our tasks JSON file
TASKS_FILE = "tasks.json"

def _load_tasks() -> list:
    """Loads tasks from the JSON file. Returns an empty list if file doesn't exist."""
    if not os.path.exists(TASKS_FILE):
        return []
    try:
        with open(TASKS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def _save_tasks(tasks: list):
    """Saves the list of tasks to the JSON file."""
    with open(TASKS_FILE, 'w') as f:
        json.dump(tasks, f, indent=4)

def add_task(description: str) -> dict:
    """
    Adds a new task to the list.

    Args:
        description: The description of the task.

    Returns:
        The newly created task dictionary.
    """
    tasks = _load_tasks()
    new_task = {
        "id": str(uuid.uuid4())[:8],  # A short, unique ID
        "description": description,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    tasks.append(new_task)
    _save_tasks(tasks)
    print(f"Task added: {new_task}")
    return new_task

def list_tasks(status_filter: str = None) -> list:
    """
    Lists all tasks, optionally filtering by status.

    Args:
        status_filter: Optional. Either 'pending' or 'completed'.

    Returns:
        A list of task dictionaries.
    """
    tasks = _load_tasks()
    if status_filter:
        return [task for task in tasks if task['status'] == status_filter]
    return tasks

def mark_task_complete(task_id: str) -> dict | None:
    """
    Marks a task as 'completed'.

    Args:
        task_id: The ID of the task to mark as complete.

    Returns:
        The updated task dictionary, or None if the task was not found.
    """
    tasks = _load_tasks()
    task_found = None
    for task in tasks:
        if task['id'] == task_id:
            task['status'] = 'completed'
            task_found = task
            break
    
    if task_found:
        _save_tasks(tasks)
        print(f"Task marked complete: {task_found}")
        return task_found
    else:
        print(f"Task not found with ID: {task_id}")
        return None