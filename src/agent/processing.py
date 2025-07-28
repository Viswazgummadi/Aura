# src/agent/processing.py

import json
import asyncio

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
        user = crud.get_user_by_google_email(db, google_email=email)
        if not user:
            print(f"ERROR: No user found for email {email}. Cannot process notification.")
            return

        # This function is NOT a tool, so we call it directly. This is correct.
        new_messages, last_history_id = gmail_tools.fetch_new_messages_for_processing_from_api(
            user_id=user.id,
            start_history_id=start_history_id
        )

        if not new_messages:
            print(f"PROACTIVE_AGENT: No new messages to process for user {user.id}.")
            return

        for message in new_messages:
            print(f"PROACTIVE_AGENT: Found new email for user {user.id}: '{message['subject']}'")
            
            # --- THIS IS THE FIX ---
            # get_email_body IS a tool, so we must call it with .invoke()
            email_body = gmail_tools.get_email_body.invoke({
                "user_id": user.id,
                "message_id": message['id']
            })
            # --- END OF FIX ---
            
            if "Error:" in email_body:
                print(f"WARN: Could not retrieve body for message {message['id']}. Skipping. Reason: {email_body}")
                continue

            full_email_content = f"From: {message['sender']}\nSubject: {message['subject']}\n\n{email_body}"

            triage_agent_graph = get_triage_agent_graph()
            initial_state = {
                "user_id": user.id,
                "email_content": full_email_content,
            }
            final_state = triage_agent_graph.invoke(initial_state)

            triage_result = final_state.get("triage_result")
            if triage_result and triage_result.action_required:
                tool_outputs = final_state.get("tool_outputs", [])
                
                summary = (
                    f"Aura took action on an email: '{message['subject']}'.\n"
                    f"Triage: {triage_result.summary}\n"
                    f"Action Result: {tool_outputs[0] if tool_outputs else 'No output.'}"
                )

                notification_payload = {
                    "type": "proactive_agent_action",
                    "data": {"summary": summary}
                }
                
                try:
                    asyncio.run(manager.send_personal_message(json.dumps(notification_payload), user.id))
                    print(f"PROACTIVE_AGENT: Sent WebSocket notification to user {user.id}")
                except Exception as e:
                    print(f"ERROR: Failed to send WebSocket notification. Details: {e}")

    finally:
        db.close()