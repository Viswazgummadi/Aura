# File: src/agent/invoker.py (Final ReAct Invoker)

import discord
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage # Added AIMessage, ToolMessage for type checking

from src.agent.graph import app, AgentState # Import the compiled ReAct agent app


async def handle_mention(message: discord.Message):
    """
    This function is the main entry point for the ReAct agent.
    It prepares the input and streams the response from the LangGraph agent.
    """
    async with message.channel.typing():
        prompt_content = message.content.replace(f'<@!{message.guild.me.id}>', '').replace(f'<@{message.guild.me.id}>', '').strip()

        if not prompt_content:
            return

        # THIS IS THE CRITICAL SYSTEM PROMPT FOR THE REACT AGENT
        # It guides its planning, tool use, conversation, and multi-step reasoning.
        system_prompt = (
            "You are Aura, a highly intelligent and helpful personal assistant for students and tech professionals. "
            "Your core purpose is to assist the user in managing their personal time, tasks, and information efficiently "
            "by using the tools available to you. You are also capable of general conversation.\n\n"
            "**Your Overall Strategy (ReAct Pattern):**\n"
            "1. **Understand:** Carefully analyze the user's request. **Crucially**, if the user is asking to add multiple tasks or mark multiple tasks as complete, you MUST break it down into individual steps for your tools.\n"
            "2. **Tool Selection & Planning:** Choose the best tool(s). If it's a complex request requiring multiple tool calls, think step-by-step. For example:\n"
            "   - To 'mark all pending tasks as complete': First, call `list_tasks(status_filter='pending')` to get their IDs. Then, for each ID obtained, call `mark_task_complete(task_id=...)` sequentially.\n"
            "   - To 'add multiple tasks in one go': Call `add_task(description=...)` for each distinct task item found in the user's request.\n"
            "   - If a tool requires arguments you don't have (e.g., a specific ID), ask the user for *precise* clarification (e.g., 'Please provide the exact ID of the task you want to mark complete.').\n"
            "3. **Act:** Execute the chosen tool(s).\n"
            "4. **Observe:** Analyze the output from the tool(s). This is crucial for planning the next step. If a tool call was successful, indicate so. If it failed, explain the failure.\n"
            "5. **Refine/Iterate:** Based on the observation, decide if more tool calls are needed to complete the original request. Loop back to Plan/Act/Observe until the task is done. **Output your intermediate thoughts (using Thought:) and actions (Action:).**\n" # Added instruction to output thoughts/actions
            "6. **Respond:** Once the task is complete, or if no tools were needed (general chat), provide a clear, concise, and helpful natural language response. Summarize actions taken. **Your final response should not contain tool calls.**\n\n"
            "**Important Rules and Guidelines:**\n"
            "- **Prioritize Tool Use:** Always use a tool if the user's intent clearly matches a tool's functionality. Do not answer conversationally if a tool should be used. Directly make the tool call.\n"
            "- **No Hallucinations:** Never claim to perform actions you cannot or have not performed. If you lack a tool for a specific request (e.g., deleting *completed* tasks, as `delete_note` is for notes, not tasks), state your limitations clearly and politely based on your *available tools*.\n"
            "- **Conciseness:** Be direct and to the point. Avoid overly verbose explanations unless specifically asked.\n"
            "- **Professionalism:** Maintain a helpful, friendly, and efficient persona (Aura).\n"
            "- **General Questions:** If a request is purely conversational and does not involve personal data or tools (e.g., 'What is LangGraph?'), answer directly using your knowledge without attempting tool calls.\n"
        )

        initial_state: AgentState = {
            "messages": [
                SystemMessage(content=system_prompt),
                HumanMessage(content=prompt_content)
            ]
        }

        try:
            accumulated_response_content = ""
            
            # Stream events from the agent graph
            async for event in app.astream(initial_state):
                # Print all events for detailed debugging
                # print(event)
                # print("----")

                # The 'agent' node is the only LLM node that produces human-readable output
                # or tool calls.
                if "agent" in event:
                    last_message_from_agent = event["agent"]["messages"][-1]
                    
                    # If the agent outputted text content (not just a tool call), accumulate it.
                    # This captures both intermediate thoughts and final answers.
                    if isinstance(last_message_from_agent, AIMessage) and last_message_from_agent.content:
                        accumulated_response_content += last_message_from_agent.content
                    
                    # If the agent provided tool_calls, those will be handled by the ToolNode.
                    # The next iteration will return to the agent node with ToolMessage.

                # If the 'action' node produced output (meaning a tool was executed)
                if "action" in event:
                    # ToolNode adds ToolMessage to the state.
                    # We might want to clear accumulated_response_content here
                    # so we only reply with the *final* response after all steps.
                    # For now, let's just let the agent's final message overwrite.
                    pass # The tool output is implicitly handled by the next agent turn.

            # After the stream completes, the final_response will be the content
            # of the last message the agent decided to send that was not a tool call.
            # We rely on the agent's prompt to ensure it provides a final summary.
            
            # This logic can be tricky with astream if the final answer is not the last event.
            # A more robust way: let the agent finish and then get the final state.
            
            # Let's try to fetch the final state after the stream.
            # This requires LangGraph 0.0.69+, but is the most reliable way to get final state.
            # If this fails, we resort to a simpler accumulation.
            
            # Simplified accumulator approach: The agent's prompt guides it to output
            # a final response. If it outputs a tool call and loops, the loop continues.
            # If it outputs a final text, the stream ends, and we capture that text.

            # The current accumulated_response_content should hold the final text response.
            if accumulated_response_content:
                await message.reply(accumulated_response_content)
            else:
                # This fallback might occur if agent only executes tools and gives no final text.
                # Or if the stream somehow terminates without a final text from agent node.
                await message.add_reaction('✅')

        except Exception as e:
            print(f"Error invoking agent graph: {e}")
            await message.reply("Sorry, I encountered an error while processing your request. Please check my console for details.")