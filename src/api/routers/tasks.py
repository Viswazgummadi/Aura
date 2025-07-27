# src/api/routers/tasks.py

from fastapi import APIRouter, Depends, HTTPException, status
from src.database.models import TaskCreate, TaskResponse, TaskUpdate, User
from src.api.dependencies import get_current_user
from src.agent.tools import tasks as tasks_tools

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_new_task(task: TaskCreate, current_user: User = Depends(get_current_user)):
    tool_input = {
        "user_id": current_user.id,
        "description": task.description,
        "priority": task.priority,
        "due_date": task.due_date.isoformat().replace('+00:00', 'Z') if task.due_date else None
    }
    return tasks_tools.create_task.invoke(tool_input)

@router.get("", response_model=list[TaskResponse])
def get_all_user_tasks(current_user: User = Depends(get_current_user)):
    return tasks_tools.get_all_tasks.invoke({"user_id": current_user.id})

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
    if "Error" in result:
        raise HTTPException(status_code=404, detail=result)
    return