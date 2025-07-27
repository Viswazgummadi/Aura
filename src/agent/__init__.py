# src/agent/tools/__init__.py

from langchain_core.tools import tool
from . import notes, tasks # Add other tool modules as we create them

# We use the @tool decorator to make our Python functions compatible with the agent.
# NOTE: We will need to go into notes.py and tasks.py to add this decorator.

# Example of what a decorated tool would look like in notes.py:
# @tool
# def search_notes(query: str) -> str:
#    """Searches the user's notes and returns the results."""
#    # ... implementation ...

# For now, let's create a placeholder list. We will populate this properly.
all_tools = [
    # notes.search_notes,
    # tasks.create_task,
    # ... etc
]