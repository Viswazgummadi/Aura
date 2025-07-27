# src/agent/tools/__init__.py

# Import the tool functions directly from their modules
from .notes import (
    create_note,
    get_all_notes,
    search_notes,
    update_note,
    delete_note,
    add_tag_to_note,
    remove_tag_from_note,
    get_notes_by_tag,
)
from .tasks import (
    create_task,
    get_all_tasks,
    update_task,
    delete_task,
)

# Define the list of all tools that the agent can use.
# This is the single source of truth for the agent's capabilities.
all_tools = [
    # Note Tools
    create_note,
    get_all_notes,
    search_notes,
    update_note,
    delete_note,
    add_tag_to_note,
    remove_tag_from_note,
    get_notes_by_tag,
    # Task Tools
    create_task,
    get_all_tasks,
    update_task,
    delete_task,
]