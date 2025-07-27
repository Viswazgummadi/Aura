# src/agent/graph/builder.py

from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.runnables import RunnableConfig

from src.agent.graph.state import AgentState
from src.core.model_manager import model_manager

# --- FIX: Explicitly import all tools and build the list here ---
from src.agent.tools.notes import (
    create_note, get_all_notes, search_notes, update_note,
    delete_note, add_tag_to_note, remove_tag_from_note, get_notes_by_tag
)
from src.agent.tools.tasks import (
    create_task, get_all_tasks, update_task, delete_task
)

all_tools = [
    create_note, get_all_notes, search_notes, update_note,
    delete_note, add_tag_to_note, remove_tag_from_note, get_notes_by_tag,
    create_task, get_all_tasks, update_task, delete_task,
]
# --- END OF FIX ---


# 1. Get the configured LLM from our resilient ModelManager
llm = ChatGoogleGenerativeAI(model=model_manager.get_active_model().model_name)

# 2. Bind our tools to the LLM
model_with_tools = llm.bind_tools(all_tools)

# 3. Define the Nodes for our Graph

class ToolExecutorNode:
    def __init__(self, tools):
        self.tool_invoker = ToolNode(tools)

    def __call__(self, state: AgentState, config: RunnableConfig):
        user_id = config["configurable"]["user_id"]
        tool_calls = state["messages"][-1].tool_calls
        
        for call in tool_calls:
            call["args"]["user_id"] = user_id
            
        return self.tool_invoker.invoke(state, config)

tool_node = ToolExecutorNode(all_tools)


def model_node(state: AgentState):
    """Primary 'brain' of the agent."""
    response = model_with_tools.invoke(state["messages"])
    return {"messages": [response]}

# 4. Define the Edges for our Graph

def should_continue(state: AgentState):
    """Router to determine the next step."""
    if state["messages"][-1].tool_calls:
        return "tools"
    return END

# 5. Build the Graph
graph_builder = StateGraph(AgentState)

graph_builder.add_node("model", model_node)
graph_builder.add_node("tools", tool_node)

graph_builder.set_entry_point("model")

graph_builder.add_conditional_edges(
    "model",
    should_continue,
    {"tools": "tools", END: END},
)

graph_builder.add_edge("tools", "model")

agent_graph = graph_builder.compile()