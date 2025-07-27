# src/agent/graph/builder.py

from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from src.agent.graph.state import AgentState
from src.agent.tools import all_tools # We will create this in the next step
from src.core.model_manager import model_manager

# 1. Get the configured LLM from our resilient ModelManager
llm = ChatGoogleGenerativeAI(model=model_manager.get_active_model().model_name)

# 2. Bind our tools to the LLM. This lets the LLM know what functions it can call.
# The `with_structured_output` part tells it to format its output as a tool call.
model_with_tools = llm.bind_tools(all_tools)

# 3. Define the Nodes for our Graph

# The ToolNode is a pre-built node that executes tools.
tool_node = ToolNode(all_tools)

def model_node(state: AgentState):
    """
    This is the primary "brain" of the agent. It decides what to do based on the conversation history.
    """
    # The model decides whether to call a tool or respond to the user.
    response = model_with_tools.invoke(state["messages"])
    return {"messages": [response]}

# 4. Define the Edges for our Graph

def should_continue(state: AgentState):
    """
    This function is our router. It determines the next step in the graph.
    """
    last_message = state["messages"][-1]
    # If the last message is a tool call, we route to the tool_node.
    if last_message.tool_calls:
        return "tools"
    # Otherwise, we are done.
    return END

# 5. Build the Graph
graph_builder = StateGraph(AgentState)

graph_builder.add_node("model", model_node)
graph_builder.add_node("tools", tool_node)

graph_builder.set_entry_point("model")

graph_builder.add_conditional_edges(
    "model",
    should_continue,
    {
        "tools": "tools",
        END: END,
    },
)

graph_builder.add_edge("tools", "model")

# The compiled graph is our ready-to-use agent.
agent_graph = graph_builder.compile()