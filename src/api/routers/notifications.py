# src/api/routers/notifications.py

import base64
import json
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status, Request
from pydantic import BaseModel, Field

# We will create this processing function in the next step
from src.agent import processing

router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"]
)

# Pydantic models to validate the incoming message from Google Pub/Sub
class PubSubMessage(BaseModel):
    data: str # This is a base64-encoded string
    message_id: str = Field(..., alias="messageId")

class PubSubPushRequest(BaseModel):
    message: PubSubMessage
    subscription: str

@router.post("/gmail", status_code=status.HTTP_204_NO_CONTENT)
async def gmail_push_notification(
    request: PubSubPushRequest,
    background_tasks: BackgroundTasks
):
    """
    Receives push notifications from Google Cloud Pub/Sub for Gmail updates.
    This endpoint must be FAST. It acknowledges the message and hands off
    the real work to a background task.
    """
    try:
        # Decode the data from base64
        payload_str = base64.b64decode(request.message.data).decode("utf-8")
        payload = json.loads(payload_str)
        
        email = payload.get("emailAddress")
        history_id = payload.get("historyId")

        if not email or not history_id:
            print(f"ERROR: Invalid payload received from Pub/Sub: {payload}")
            # Still return a 204 so Google doesn't retry a bad message
            return

        print(f"INFO: Received Gmail push for {email}. Queueing for background processing.")

        # This is the key! Add the heavy lifting to the background.
        # FastAPI will execute this *after* sending the 204 response.
        background_tasks.add_task(
            processing.process_new_email_notification,
            email=email,
            new_history_id=history_id
        )

    except Exception as e:
        print(f"CRITICAL: Error processing Pub/Sub message: {e}")
        # In case of failure, we still return a success status code to prevent
        # Google from spamming us with retries for a message we can't process.
        # We rely on our own logs to catch the failure.
    
    return