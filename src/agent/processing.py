# src/agent/processing.py

import json
import asyncio
from langchain_core.messages import HumanMessage

from src.agent.graph.builder import get_agent_graph
from src.agent.tools import gmail as gmail_tools
from src.database import crud, database
from src.api.connection_manager import manager

def process_new_email_notification(email: str, start_history_id: int):
    """
    This function runs in the background. It fetches new emails and invokes
    the main conversational agent to process them.
    """
    print(f"PROACTIVE_AGENT: Processing started for {email} from historyId {start_history_id}")
    db = database.SessionLocal()
    try:
        user = crud.get_user_by_google_email(db, google_email=email)
        if not user:
            print(f"ERROR: No user found for Google email {email}. Cannot process notification.")
            return

        new_messages, _ = gmail_tools.fetch_new_messages_for_processing_from_api(
            user_id=user.id,
            start_history_id=start_history_id
        )

        if not new_messages:
            print(f"PROACTIVE_AGENT: No new messages to process for user {user.id}.")
            return

        agent_graph = get_agent_graph()
        config = {"configurable": {"user_id": user.id}}

        for message in new_messages:
            print(f"PROACTIVE_AGENT: Found new email for user {user.id}: '{message['subject']}'")
            email_body = gmail_tools.get_email_body.invoke({
                "user_id": user.id, "message_id": message['id']
            })
            
            if "Error:" in email_body:
                print(f"WARN: Could not retrieve body for message {message['id']}. Skipping.")
                continue

            # We simulate a user prompt to the conversational agent
            simulated_prompt = (
                "A new email has arrived in my inbox. Please analyze it and take the most appropriate action based on its content. "
                "If it's a task or meeting, create it. If it's junk, ignore it. Summarize your actions for me.\n\n"
                f"--- EMAIL START ---\n"
                f"From: {message['sender']}\n"
                f"Subject: {message['subject']}\n\n"
                f"{email_body}\n"
                f"--- EMAIL END ---"
            )
            
            # Invoke the main agent with this simulated prompt
            response = agent_graph.invoke({
                "messages": [HumanMessage(content=simulated_prompt)]
            }, config=config)

            final_response_message = response['messages'][-1].content
            
            notification_payload = {
                "type": "proactive_agent_action",
                "data": {"summary": final_response_message}
            }
            
            try:
                asyncio.run(manager.send_personal_message(json.dumps(notification_payload), user.id))
                print(f"PROACTIVE_AGENT: Sent WebSocket notification to user {user.id}")
            except Exception as e:
                print(f"ERROR: Failed to send WebSocket notification. Details: {e}")
    finally:
        db.close()