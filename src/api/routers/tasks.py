# src/api/routers/tasks.py

from fastapi import APIRouter, Depends, HTTPException, status, Query
from src.database.models import TaskCreate, TaskResponse, TaskUpdate, User
from src.api.dependencies import get_current_user
from src.agent.tools import tasks as tasks_tools
from typing import Optional

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_new_task(task: TaskCreate, current_user: User = Depends(get_current_user)):
    # --- THIS IS THE FIX ---
    
    # 1. Let Pydantic convert the incoming request data into a dictionary.
    #    This will now automatically include `status` if it was provided.
    tool_input = task.model_dump(exclude_unset=True)
    
    # 2. Add the user_id, which is not part of the request body.
    tool_input['user_id'] = current_user.id

    # 3. Handle the due_date format conversion if it exists.
    if 'due_date' in tool_input and tool_input['due_date']:
        tool_input['due_date'] = tool_input['due_date'].isoformat().replace('+00:00', 'Z')

    # 4. Invoke the tool with the complete dictionary.
    return tasks_tools.create_task.invoke(tool_input)

@router.get("", response_model=list[TaskResponse])
def get_all_user_tasks(
    current_user: User = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter tasks by status (e.g., 'pending', 'completed')"),
    priority: Optional[str] = Query(None, description="Filter tasks by priority (e.g., 'high', 'medium', 'low')")
):
    """
    Get a list of all tasks for the current user.
    You can optionally filter the tasks by their status or priority.
    """
    # We pass the query parameters directly to the tool's invoke method.
    tool_input = {"user_id": current_user.id}
    if status:
        tool_input["status"] = status
    if priority:
        tool_input["priority"] = priority
        
    return tasks_tools.get_all_tasks.invoke(tool_input)

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