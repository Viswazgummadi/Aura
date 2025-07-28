# src/agent/graph/triage.py

import json
import pydantic # Import pydantic for the validation error
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langchain.tools.render import render_text_description

from src.agent.graph.state import TriageState, TriageResult
from src.core.model_manager import model_manager
from src.agent.graph.builder import all_tools # Import the master tool list
import datetime

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
        
        active_model = model_manager.get_active_model()
        llm = ChatGoogleGenerativeAI(model=active_model.model_name)
        structured_llm = llm.with_structured_output(TriageResult)

        triage_prompt = ChatPromptTemplate.from_template(
        """
        You are a world-class, proactive executive assistant. Your primary function is to analyze email content and translate it into a structured, actionable plan. You must be thorough, precise, and use your intelligence to infer missing information.

        **Your Goal:**
        Analyze the email content and populate the JSON schema. Your main goal is to determine if an action is required and to extract or infer every piece of information needed for that action.

        **Your Core Principles of Inference:**
        - **Assume Standard Deadlines:** If a deadline is not specified for a task, assume a reasonable default, such as the end of the next business day.
        - **Infer Priority from Context:** Analyze the language of the email. If it contains words like "urgent," "important," or "asap," you MUST set the `urgency` score to 8 or higher. If the language is casual or informational, a lower urgency is appropriate.
        - **Default to Action:** If an email contains a clear task or meeting request, `action_required` should be `True` even if some details are missing. It is your job to fill in the blanks with reasonable defaults.

        **Instructions for `extracted_entities`:**
        - This field MUST be a valid JSON dictionary.
        - Be aggressive in your extraction. It is better to extract partial information than nothing at all.
        - **For a DEADLINE_TASK:** You MUST extract `task_description` and `due_date`. Example: {{"task_description": "Submit the quarterly report", "due_date": "Friday at 5pm"}}
        - **For a MEETING_REQUEST:** You MUST extract `title`, and if available, `attendees`, and `proposed_time`. Example: {{"title": "Project Sync", "proposed_time": "next Tuesday at 2pm"}}
        - If you are absolutely certain no entities can be extracted, provide an empty dictionary: {{}}

        **Crucially, the value for `extracted_entities` must be a valid JSON object/dictionary, NOT a stringified JSON.**

        Email Content:
        ---
        {email_content}
        ---
        """
        )
        planning_prompt_template = ChatPromptTemplate.from_template(
        """
        You are a meticulous and intelligent planning agent. Your goal is to construct a perfect tool call based on the user's needs.

        **Triage Analysis:**
        The email has been classified as: {triage_result}

        **Full Email Content:**
        ---
        {email_content}
        ---

        **Available Tools:**
        {tools}

        **Your Task:**
        Based on the Triage Analysis AND the full email content, construct a single, valid JSON tool call to address the user's needs.
        - You MUST use the full email content to find the specific arguments for the tool (like summary, dates, times, or descriptions).
        - If the triage classified the email as a `DEADLINE_TASK`, you MUST call the `create_task` tool.
        - If the triage classified the email as a `MEETING_REQUEST`, you MUST call the `create_calendar_event` tool.
        - Be intelligent in parsing dates and times from the text. The current time is {current_time}.
        - If you are absolutely certain that no tool call can or should be made, respond with an empty JSON object {{}}.
        """
        )
        planning_agent = planning_prompt_template | llm.bind_tools(all_tools)

        def triage_email_node(state: TriageState):
            """
            First node: Analyzes the email and produces a structured TriageResult.
            This node is built to be resilient with retries and robust parsing.
            """
            print("TRIAGE_AGENT: Triaging email...")
            chain = triage_prompt | structured_llm
            
            # --- THE BULLETPROOF FIX ---
            # Add a retry loop to handle intermittent LLM failures or formatting errors.
            for i in range(3):
                try:
                    result = chain.invoke({"email_content": state["email_content"]})
                    
                    # Defensively parse the LLM's output.
                    if isinstance(result.extracted_entities, str):
                        # Clean up potential markdown and newlines before parsing.
                        cleaned_string = result.extracted_entities.strip().replace('```json', '').replace('```', '').strip()
                        result.extracted_entities = json.loads(cleaned_string)
                    
                    # If we get here, validation was successful.
                    print(f"TRIAGE_AGENT: Triage result: {result}")
                    return {"triage_result": result}

                except (json.JSONDecodeError, pydantic.ValidationError) as e:
                    # If parsing or validation fails, we log the error and try again.
                    print(f"WARN: Attempt {i+1} failed. Pydantic/JSON error: {e}. Retrying...")
                    if i == 2: # If it's the last attempt, we give up.
                        print("ERROR: Failed to triage email after multiple retries.")
                        # We create a safe, empty result to prevent the whole graph from crashing.
                        empty_result = TriageResult(
                            email_type="INFO_UPDATE", urgency=1, summary="Could not process email.",
                            action_required=False, extracted_entities={}
                        )
                        return {"triage_result": empty_result}
            
            raise Exception("Failed to triage email after multiple retries.")


        def planning_node(state: TriageState):
            """Second node: Decides which tool to call based on the triage result and full email content."""
            if not state["triage_result"].action_required:
                print("TRIAGE_AGENT: No action required.")
                return {"plan": []}
            
            print("TRIAGE_AGENT: Planning tool call...")
            tool_description = render_text_description(all_tools)
            
            # --- THIS IS THE FIX ---
            # We now provide the full email content and current time to the planner.
            current_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
            plan = planning_agent.invoke({
                "triage_result": state["triage_result"].dict(),
                "email_content": state["email_content"], # Give the planner the raw material
                "tools": tool_description,
                "current_time": current_time
            })
            # --- END OF FIX ---
            
            print(f"TRIAGE_AGENT: Plan generated: {plan.tool_calls}")
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

        def should_execute_tool(state: TriageState):
            return "execute_tool" if state.get("plan") and state["plan"] else END

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