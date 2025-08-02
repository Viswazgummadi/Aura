# src/agent/tools/__init__.py

"""
A single point of entry to gather and export all available agent tools.

This file uses a feature of LangChain's `@tool` decorator, which automatically
adds decorated functions to a `__tools__` list in their respective modules.
We then collect all these lists into one master list.
"""

from . import tasks as tasks_tools
from . import notes as notes_tools
from . import calendar as calendar_tools
from . import gmail as gmail_tools
from . import settings as settings_tools
from .tasks import create_task
from .notes import create_note
from .calendar import create_calendar_event
from .gmail import list_unread_emails
# We expect each imported module to have a `__tools__` list populated by the @tool decorator.
# The `getattr` function is used safely, providing an empty list `[]` as a default
# if a module happens to not have any tools defined, preventing an error.
all_tools = (
    getattr(tasks_tools, '__tools__', []) +
    getattr(notes_tools, '__tools__', []) +
    getattr(calendar_tools, '__tools__', []) +
    getattr(gmail_tools, '__tools__', []) +
    getattr(settings_tools, '__tools__', [])
)
