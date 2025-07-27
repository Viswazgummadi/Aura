# src/agent/graph/builder.py

import datetime
from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
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
from src.agent.tools.calendar import (
    list_upcoming_events, create_calendar_event, update_calendar_event, delete_calendar_event
)
from src.agent.tools.gmail import (
    list_unread_emails, get_email_body, send_email, mark_email_as_read
)

# This is the complete list of capabilities for the Aura agent.
all_tools = [
    # Note Tools
    create_note, get_all_notes, search_notes, update_note,
    delete_note, add_tag_to_note, remove_tag_from_note, get_notes_by_tag,
    # Task Tools
    create_task, get_all_tasks, update_task, delete_task,
    # Calendar Tools
    list_upcoming_events, create_calendar_event, update_calendar_event, delete_calendar_event,
    # Gmail Tools
    list_unread_emails, get_email_body, send_email, mark_email_as_read,
]
# --- Global variable to hold our compiled graph ---
_agent_graph = None

def get_agent_graph():
    """
    This function builds and returns the agent graph.
    It uses a global variable to ensure the graph is only built once (lazy loading).
    """
    global _agent_graph
    if _agent_graph is None:
        print("INFO: Building agent graph for the first time...")
        
        # 1. The System Prompt: This is the agent's personality and instructions.
        SYSTEM_PROMPT = """
You are Aura, a world-class, super-intelligent personal assistant. Your user is conversing with you.

**Your Core Principles:**
- You are friendly, proactive, and exceptionally helpful.
- Your primary goal is to reduce the user's workload and cognitive load.
- You must be aware of the current date and time to reason about deadlines. The current UTC time is {current_time}.
- You MUST NEVER ask for the `user_id`. It is provided to you automatically in the background for every tool call. You must act as if you already know who the user is.

**Reasoning and Tool Use Strategy:**
- **Tool First:** If the user's request can be fulfilled by using one of your tools, you MUST use the tool. Do not answer from your own knowledge or memory if a tool is available. Only respond to the user after the tool has been called and you have its output.
- **Infer, Don't Ask:** If the user's intent is clear, act on it directly. Do not ask for confirmation on obvious tasks.
- **Be Flexible with Inputs:** The user is human. It is your job to translate their vague language into the structured format the tools require.
    - If a user says a deadline is "tomorrow", "next Friday", or "in 2 days", calculate the actual date and provide it in 'YYYY-MM-DDTHH:MM:SSZ' format.
    - If a user gives a vague priority like "super serious", map it to 'high'. If they say "whenever", map it to 'low'.

**Example Thought Process:**
User message: "hey can you remind me to pick up the dry cleaning tomorrow evening"
Your thought process:
1. The user wants a reminder, which is a task. The `create_task` tool is appropriate.
2. The description is "pick up the dry cleaning".
3. The due date is "tomorrow evening". I will calculate that and format it as 'YYYY-MM-DDTHH:18:00:00Z'.
4. I will now call the `create_task` tool with these arguments.
(After the tool call succeeds, you can then generate your friendly response to the user).
"""

        # 2. The Agent Prompt Template
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        # 3. Get the configured LLM from our resilient ModelManager
        active_model = model_manager.get_active_model()
        if not active_model:
            raise RuntimeError("Cannot build agent graph: No active LLM model configured.")
        llm = ChatGoogleGenerativeAI(model=active_model.model_name)
        
        # 4. Bind our tools to the LLM
        llm_with_tools = llm.bind_tools(all_tools)

        # 5. Create the Agent Chain
        agent_chain = prompt | llm_with_tools

        # 6. Define the Nodes
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
            current_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
            response = agent_chain.invoke({
                "messages": state["messages"],
                "current_time": current_time
            })
            return {"messages": [response]}

        # 7. Define the Edges
        def should_continue(state: AgentState):
            if state["messages"][-1].tool_calls:
                return "tools"
            return END

        # 8. Build the Graph
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