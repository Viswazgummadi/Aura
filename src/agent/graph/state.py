# src/agent/graph/state.py

from typing import TypedDict, Annotated, List
from langchain_core.messages import BaseMessage
import operator

# This is the agent's "memory" or "scratchpad" that gets passed around.
class AgentState(TypedDict):
    # Each step of the conversation is added to this list.
    messages: Annotated[List[BaseMessage], operator.add]