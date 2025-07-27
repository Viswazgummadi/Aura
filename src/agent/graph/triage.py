# src/agent/graph/triage.py

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END

from src.agent.graph.state import TriageState, TriageResult
from src.core.model_manager import model_manager
# We need to import the tools to execute them
from src.agent.graph.builder  import all_tools
from langchain.tools.render import render_text_description

# 1. Initialize the LLM and bind it to our TriageResult schema
active_model = model_manager.get_active_model()
llm = ChatGoogleGenerativeAI(model=active_model.model_name)
structured_llm = llm.with_structured_output(TriageResult)

# 2. Define the Prompts
triage_prompt = ChatPromptTemplate.from_template(
"""
You are an expert email triaging assistant. Analyze the following email content and classify it according to the provided JSON schema.
Your goal is to determine if an action is required and extract all necessary information for that action.

Email Content:
---
{email_content}
---
"""
)

planning_prompt_template = ChatPromptTemplate.from_template(
"""
You are an expert planning agent. Based on the triage of an email, formulate a plan to take action.
Your goal is to choose the single best tool to call to address the user's needs.

Available Tools:
{tools}

Triage Result:
---
{triage_result}
---

Based on the triage result, which tool should be called? Respond with a single, valid JSON tool call.
If no action is needed, respond with an empty JSON object {{}}.
"""
)

# 3. Create the Agent Chain for Planning
planning_agent = planning_prompt_template | llm.bind_tools(all_tools)

# 4. Define the Nodes of the Graph

def triage_email_node(state: TriageState):
    """First node: Analyzes the email and produces a structured TriageResult."""
    print("TRIAGE_AGENT: Triaging email...")
    chain = triage_prompt | structured_llm
    result = chain.invoke({"email_content": state["email_content"]})
    print(f"TRIAGE_AGENT: Triage result: {result}")
    return {"triage_result": result}

def planning_node(state: TriageState):
    """Second node: Decides which tool to call based on the triage result."""
    if not state["triage_result"].action_required:
        print("TRIAGE_AGENT: No action required.")
        return {"plan": []}
    
    print("TRIAGE_AGENT: Planning tool call...")
    tool_description = render_text_description(all_tools)
    plan = planning_agent.invoke({
        "triage_result": state["triage_result"].dict(),
        "tools": tool_description
    })
    print(f"TRIAGE_AGENT: Plan generated: {plan.tool_calls}")
    return {"plan": plan.tool_calls}

def tool_executor_node(state: TriageState):
    """Third node: Executes the planned tool call."""
    tool_calls = state.get("plan", [])
    if not tool_calls:
        return {"tool_outputs": []}
        
    print(f"TRIAGE_AGENT: Executing tool call: {tool_calls[0]}")
    # This is a simplified executor for a single tool call
    tool_map = {tool.name: tool for tool in all_tools}
    tool_call = tool_calls[0]
    tool_to_call = tool_map.get(tool_call['name'])
    
    # Inject the user_id into the tool call arguments
    tool_args = tool_call['args']
    tool_args['user_id'] = state['user_id']
    
    if tool_to_call:
        result = tool_to_call.invoke(tool_args)
        return {"tool_outputs": [result]}
    return {"tool_outputs": [{"error": "Tool not found."}]}

# 5. Define the Edges (Conditional Logic)
def should_execute_tool(state: TriageState):
    """Router: Decides if we should execute a tool or end the process."""
    if state.get("plan"):
        return "execute_tool"
    return END

# 6. Build the Graph
graph_builder = StateGraph(TriageState)

graph_builder.add_node("triage_email", triage_email_node)
graph_builder.add_node("plan_action", planning_node)
graph_builder.add_node("execute_tool", tool_executor_node)

graph_builder.set_entry_point("triage_email")
graph_builder.add_edge("triage_email", "plan_action")
graph_builder.add_conditional_edges(
    "plan_action",
    should_execute_tool,
    { "execute_tool": "execute_tool", END: END }
)
graph_builder.add_edge("execute_tool", END)

# Compile the final graph
triage_agent_graph = graph_builder.compile()