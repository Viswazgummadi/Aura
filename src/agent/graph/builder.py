# src/agent/graph/builder.py

from langchain_core.messages import ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.runnables import RunnableConfig

from src.agent.graph.state import AgentState
from src.core.model_manager import model_manager

# --- The list of all tools available to the agent ---
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

# --- Global variable to hold our compiled graph ---
# We initialize it to None. It will be built on the first request.
_agent_graph = None

def get_agent_graph():
    """
    This function builds and returns the agent graph.
    It uses a global variable to ensure the graph is only built once (lazy loading).
    """
    global _agent_graph
    if _agent_graph is None:
        print("INFO: Building agent graph for the first time...")
        
        # 1. Get the configured LLM from our resilient ModelManager
        # By now, the DB is guaranteed to exist.
        active_model = model_manager.get_active_model()
        if not active_model:
            raise RuntimeError("Cannot build agent graph: No active LLM model configured.")
        llm = ChatGoogleGenerativeAI(model=active_model.model_name)
        
        # 2. Bind our tools to the LLM
        model_with_tools = llm.bind_tools(all_tools)

        # 3. Define the Nodes
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
            response = model_with_tools.invoke(state["messages"])
            return {"messages": [response]}

        # 4. Define the Edges
        def should_continue(state: AgentState):
            if state["messages"][-1].tool_calls:
                return "tools"
            return END

        # 5. Build the Graph
        graph_builder = StateGraph(AgentState)
        graph_builder.add_node("model", model_node)
        graph_builder.add_node("tools", tool_node)
        graph_builder.set_entry_point("model")
        graph_builder.add_conditional_edges(
            "model", should_continue, {"tools": "tools", END: END}
        )
        graph_builder.add_edge("tools", "model")

        _agent_graph = graph_builder.compile()
        print("INFO: Agent graph built successfully.")

    return _agent_graph