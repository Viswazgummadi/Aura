# File: src/agent/graph.py (Final ReAct Agent)

import sys
import os
import operator
from typing import TypedDict, Annotated, Sequence

# --- Path Fix ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# --- End Path Fix ---

from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from src.agent.core import model # This is our BASE model from core.py
from src.agent.tools import calendar as calendar_tool
from src.agent.tools import notes as notes_tool
from src.agent.tools import tasks as tasks_tool


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]


tools = [
    tasks_tool.list_tasks,
    tasks_tool.add_task,
    tasks_tool.mark_task_complete,
    notes_tool.get_note,
    notes_tool.save_note,
    notes_tool.delete_note,
    calendar_tool.fetch_upcoming_events,
    calendar_tool.create_new_event
]

model_with_tools = model.bind_tools(tools)
tool_node = ToolNode(tools)


# --- NODES ---

def agent_node(state: AgentState):
    print("--- Node: Agent (Thinking & Planning) ---")
    messages = state['messages']
    
    # The system prompt should be the first message.
    # The invoker will ensure this is the case.
    
    response = model_with_tools.invoke(messages) # LLM has access to tools
    return {"messages": [response]}


# --- EDGES / ROUTING LOGIC ---

def should_continue(state: AgentState):
    last_message = state['messages'][-1]
    if last_message.tool_calls:
        print("--- Decision: Agent wants to call a tool ---")
        return "action"
    print("--- Decision: Agent has a final answer or needs clarification (END) ---")
    return "end"


# --- GRAPH DEFINITION ---

workflow = StateGraph(AgentState)

workflow.add_node("agent", agent_node)
workflow.add_node("action", tool_node)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "action": "action",
        "end": END,
    },
)

workflow.add_edge("action", "agent")

app = workflow.compile()
print("LangGraph ReAct agent compiled successfully.")


if __name__ == "__main__":
    print("\n--- Running Graph Visualization ---")
    try:
        image_bytes = app.get_graph().draw_png()
        image_path = os.path.join(project_root, "agent_graph.png")
        with open(image_path, "wb") as f:
            f.write(image_bytes)
        print(f"Successfully generated {image_path}")
    except Exception as e:
        print(f"\nCould not generate PNG. Is graphviz installed on your system?")
        print(f"Error details: {e}")