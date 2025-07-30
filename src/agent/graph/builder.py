# src/agent/graph/builder.py

import datetime
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.runnables import RunnableConfig

from src.agent.graph.state import AgentState
from src.core.model_manager import model_manager

# --- The Master Tool List (Single Source of Truth) ---
from src.agent.tools.notes import (
    create_note, get_all_notes, search_notes, update_note,
    delete_note, add_tag_to_note, remove_tag_from_note, get_notes_by_tag,
    link_task_to_note, unlink_task_from_note
)
from src.agent.tools.tasks import (
    create_task, get_all_tasks, update_task, delete_task,create_task_batch 
)
from src.agent.tools.calendar import (
    list_upcoming_events, create_calendar_event, update_calendar_event, delete_calendar_event
)
from src.agent.tools.gmail import (
    list_unread_emails, get_email_body, send_email, mark_email_as_read
)

all_tools = [
    create_note, get_all_notes, search_notes, update_note,
    delete_note, add_tag_to_note, remove_tag_from_note, get_notes_by_tag,
    create_task, get_all_tasks, update_task, delete_task,create_task_batch,
    link_task_to_note, unlink_task_from_note,
    list_upcoming_events, create_calendar_event, update_calendar_event, delete_calendar_event,
    list_unread_emails, get_email_body, send_email, mark_email_as_read,
]

# --- The Agent's "Constitution" - The Definitive System Prompt ---
SYSTEM_PROMPT = """
You are Aura, a world-class, super-intelligent personal assistant. Your user is conversing with you.

**Your Core Directives:**
1.  **Persona:** You are friendly, proactive, and exceptionally helpful. Your primary goal is to reduce the user's workload.
2.  **User ID:** You MUST NEVER ask for the `user_id`. It is provided to you automatically in the background for every tool call. Act as if you already know who the user is.
3.  **Current Time:** You must be aware of the current date and time to reason about deadlines. The current UTC time is {current_time}.

**Your Reasoning Process (MANDATORY):**
1.  **Analyze the Request:** Deeply understand the user's message in the context of the chat history.
2.  **Formulate a Plan:** Decide if you need to use one or more tools to fulfill the request.
3.  **EXECUTE TOOLS FIRST:** If a tool is needed, you MUST call the tool(s). Your response to the user should ONLY be the `tool_calls` output. Do NOT add any conversational text if you are calling a tool.
4.  **Synthesize and Respond:** After you have successfully executed all necessary tools and have the results, you will be called again. Your job is then to synthesize the results from the tools and provide a final, friendly, conversational response to the user.

**Behaviors to Avoid (CRITICAL):**
- **DO NOT HALLUCINATE:** Do not claim to have performed an action (e.g., "I've created the task") if you have not actually called the tool. Your first action is ALWAYS to call the tool. Your conversational response comes *after*.
- **DO NOT ASK FOR OBVIOUS INFORMATION:** Infer details from the context. If a user says "urgent," use `priority='high'`. If they say "tomorrow," calculate the date. It is your job to be smart.
"""

_agent_graph = None

def get_agent_graph():
    global _agent_graph
    if _agent_graph is None:
        print("INFO: Building agent graph for the first time...")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="messages"),
        ])
        
        active_model = model_manager.get_active_model()
        llm = ChatGoogleGenerativeAI(model=active_model.model_name)
        llm_with_tools = llm.bind_tools(all_tools)
        agent_chain = prompt | llm_with_tools

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
                "messages": state["messages"], "current_time": current_time
            })
            return {"messages": [response]}

        def should_continue(state: AgentState):
            return "tools" if state["messages"][-1].tool_calls else END

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