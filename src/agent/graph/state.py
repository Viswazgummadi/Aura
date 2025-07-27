# src/agent/graph/state.py

from typing import TypedDict, Annotated, List, Optional
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field
import operator
# This is the agent's "memory" or "scratchpad" that gets passed around.
class AgentState(TypedDict):
    # Each step of the conversation is added to this list.
    messages: Annotated[List[BaseMessage], operator.add]
    
class TriageResult(BaseModel):
    """The structured result of the initial email triage."""
    email_type: str = Field(description="The category of the email. Must be one of: 'MEETING_REQUEST', 'DEADLINE_TASK', 'INFO_UPDATE', 'JUNK', 'CONVERSATION'.")
    urgency: int = Field(description="The urgency of the email on a scale of 1-10.")
    summary: str = Field(description="A one-sentence summary of the email's content.")
    action_required: bool = Field(description="True if a tool should be called, False otherwise.")
    extracted_entities: Optional[dict] = Field(description="A dictionary of extracted entities like dates or topics. MUST be a valid JSON object, not a string.")

# --- NEW: State for the Triage Agent ---
class TriageState(TypedDict):
    user_id: int
    email_content: str
    triage_result: TriageResult
    plan: list # A list of tool calls to be executed
    tool_outputs: list # The results from executing the tools
    summary: str # The final summary to send to the user