# src/agent/processing.py

import json
import asyncio

# Correctly import the builder function, not the graph instance
from src.agent.graph.triage import get_triage_agent_graph
from src.agent.tools import gmail as gmail_tools
from src.database import crud, database
from src.api.connection_manager import manager

def process_new_email_notification(email: str, start_history_id: int):
    """
    This function runs in the background. It is the main entry point for the proactive agent.
    It fetches new emails and invokes the triage agent graph for each one.
    """
    print(f"PROACTIVE_AGENT: Processing started for {email} from historyId {start_history_id}")
    db = database.SessionLocal()
    try:
        # 1. Get the user from the database by their email
        user = crud.get_user_by_email(db, email=email)
        if not user:
            print(f"ERROR: No user found for email {email}. Cannot process notification.")
            return

        # 2. Use the gmail_tool to fetch the actual new message(s)
        # Note: we call the tool function directly, not via .invoke()
        new_messages, last_history_id = gmail_tools.fetch_new_messages_for_processing_from_api(
            user_id=user.id,
            start_history_id=start_history_id
        )

        if not new_messages:
            print(f"PROACTIVE_AGENT: No new messages to process for user {user.id}.")
            return

        # 3. For each new message, invoke the triage agent
        for message in new_messages:
            print(f"PROACTIVE_AGENT: Found new email for user {user.id}: '{message['subject']}'")
            
            # Get the full body of the email to provide context to the agent
            # Call the tool function directly
            email_body = gmail_tools.get_email_body(
                user_id=user.id,
                message_id=message['id']
            )
            
            if "Error:" in email_body:
                print(f"WARN: Could not retrieve body for message {message['id']}. Skipping. Reason: {email_body}")
                continue

            full_email_content = f"From: {message['sender']}\nSubject: {message['subject']}\n\n{email_body}"

            # 4. Get the Triage Agent Graph (it will be built on the first request)
            triage_agent_graph = get_triage_agent_graph()

            # 5. Invoke the Triage Agent Graph
            initial_state = {
                "user_id": user.id,
                "email_content": full_email_content,
            }
            final_state = triage_agent_graph.invoke(initial_state)

            # 6. Send a notification to the user about the action taken
            triage_result = final_state.get("triage_result")
            if triage_result and triage_result.action_required:
                tool_outputs = final_state.get("tool_outputs", [])
                
                # Formulate a summary of what the agent did
                summary = (
                    f"Aura took action on an email: '{message['subject']}'.\n"
                    f"Triage: {triage_result.summary}\n"
                    f"Action Result: {tool_outputs[0] if tool_outputs else 'No output.'}"
                )

                notification_payload = {
                    "type": "proactive_agent_action",
                    "data": {
                        "summary": summary
                    }
                }
                
                # Send the notification via WebSocket
                try:
                    asyncio.run(manager.send_personal_message(
                        json.dumps(notification_payload),
                        user.id
                    ))
                    print(f"PROACTIVE_AGENT: Sent WebSocket notification to user {user.id}")
                except Exception as e:
                    print(f"ERROR: Failed to send WebSocket notification for proactive agent. Details: {e}")

    finally:
        db.close()