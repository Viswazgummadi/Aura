# src/agent/graph/triage.py

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langchain.tools.render import render_text_description

from src.agent.graph.state import TriageState, TriageResult
from src.core.model_manager import model_manager
from src.agent.graph.builder import all_tools # Import the master tool list

# --- Global variable to hold our compiled graph ---
_triage_agent_graph = None

def get_triage_agent_graph():
    """
    This function builds and returns the triage agent graph.
    It uses a global variable to ensure the graph is only built once (lazy loading).
    """
    global _triage_agent_graph
    if _triage_agent_graph is None:
        print("INFO: Building Triage Agent graph for the first time...")
        
        # 1. Initialize the LLM (This now happens safely inside the function)
        active_model = model_manager.get_active_model()
        llm = ChatGoogleGenerativeAI(model=active_model.model_name)
        structured_llm = llm.with_structured_output(TriageResult)

        # 2. Define Prompts
        triage_prompt = ChatPromptTemplate.from_template(
        """
        You are an expert email triaging assistant. Analyze the following email content and classify it according to the provided JSON schema.
        Your goal is to determine if an action is required and extract all necessary information for that action.

        **Instructions for `extracted_entities`:**
        - This field MUST be a dictionary.
        - For a DEADLINE_TASK, extract the task description and due date. Example: {{"task_description": "Submit report", "due_date": "YYYY-MM-DDTHH:MM:SSZ"}}
        - For a MEETING_REQUEST, extract the title, attendees, and proposed time. Example: {{"title": "Project Sync", "attendees": ["bob@example.com"], "proposed_time": "..."}}
        - For other types, extract the main topic. Example: {{"topic": "Bus schedule update"}}
        - If no specific entities can be extracted, provide an empty dictionary: {{}}

        Email Content:
        ---
        {email_content}
        ---
        """
        )
        planning_prompt_template = ChatPromptTemplate.from_template(
            "You are an expert planning agent. Based on the triage of an email, choose the single best tool to call.\n"
            "Available Tools:\n{tools}\n\nTriage Result:\n---\n{triage_result}\n---\n"
            "Respond with a single, valid JSON tool call. If no action is needed, respond with an empty JSON object {{}}."
        )
        planning_agent = planning_prompt_template | llm.bind_tools(all_tools)

        # 3. Define Nodes
        def triage_email_node(state: TriageState):
            chain = triage_prompt | structured_llm
            result = chain.invoke({"email_content": state["email_content"]})
            return {"triage_result": result}

        def planning_node(state: TriageState):
            if not state["triage_result"].action_required:
                return {"plan": []}
            tool_description = render_text_description(all_tools)
            plan = planning_agent.invoke({
                "triage_result": state["triage_result"].dict(), "tools": tool_description
            })
            return {"plan": plan.tool_calls}

        def tool_executor_node(state: TriageState):
            tool_calls = state.get("plan", [])
            if not tool_calls: return {"tool_outputs": []}
            tool_map = {tool.name: tool for tool in all_tools}
            tool_call = tool_calls[0]
            tool_to_call = tool_map.get(tool_call['name'])
            tool_args = tool_call['args']
            tool_args['user_id'] = state['user_id']
            if tool_to_call:
                result = tool_to_call.invoke(tool_args)
                return {"tool_outputs": [result]}
            return {"tool_outputs": [{"error": "Tool not found."}]}

        # 4. Define Edges
        def should_execute_tool(state: TriageState):
            return "execute_tool" if state.get("plan") and state["plan"] else END

        # 5. Build Graph
        graph_builder = StateGraph(TriageState)
        graph_builder.add_node("triage_email", triage_email_node)
        graph_builder.add_node("plan_action", planning_node)
        graph_builder.add_node("execute_tool", tool_executor_node)
        graph_builder.set_entry_point("triage_email")
        graph_builder.add_edge("triage_email", "plan_action")
        graph_builder.add_conditional_edges(
            "plan_action", should_execute_tool, {"execute_tool": "execute_tool", END: END}
        )
        graph_builder.add_edge("execute_tool", END)
        _triage_agent_graph = graph_builder.compile()
        print("INFO: Triage Agent graph built successfully.")

    return _triage_agent_graph