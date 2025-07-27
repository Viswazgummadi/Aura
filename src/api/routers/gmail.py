# src/api/routers/gmail.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

# Import all necessary models and dependencies
from src.database.models import GmailMessageResponse, User, GmailSendRequest
from src.api.dependencies import get_current_user
from src.agent.tools import gmail as gmail_tools
from src.agent.tools import gmail_watcher # This tool is for admin actions

router = APIRouter(
    prefix="/gmail",
    tags=["Gmail"]
)

@router.get("/unread", response_model=List[GmailMessageResponse])
def get_unread_emails(current_user: User = Depends(get_current_user), max_results: int = 10):
    """API endpoint to retrieve a list of unread emails."""
    emails = gmail_tools.list_unread_emails.invoke({
        "user_id": current_user.id, "max_results": max_results
    })
    # Check if the tool returned an error
    if isinstance(emails, list) and emails and "error" in emails[0]:
        raise HTTPException(status_code=500, detail=emails[0]["error"])
    return emails

@router.get("/{message_id}/body", response_model=str)
def get_email_body_content(message_id: str, current_user: User = Depends(get_current_user)):
    """API endpoint to retrieve the plain text body of a specific email."""
    body = gmail_tools.get_email_body.invoke({
        "user_id": current_user.id, "message_id": message_id
    })
    if body.startswith("Error:"):
        # Differentiate between a 404 and a 500 error
        if "retrieve" in body or "not found" in body:
            raise HTTPException(status_code=404, detail=body)
        raise HTTPException(status_code=500, detail=body)
    return body

@router.post("/send", status_code=status.HTTP_201_CREATED)
def send_new_email(email_data: GmailSendRequest, current_user: User = Depends(get_current_user)):
    """API endpoint to compose and send a new email."""
    result = gmail_tools.send_email.invoke({
        "user_id": current_user.id,
        "to": email_data.to,
        "subject": email_data.subject,
        "body": email_data.body
    })
    if "error" in result:
        if "Permission denied" in result["error"]:
             raise HTTPException(status_code=403, detail=result["error"])
        raise HTTPException(status_code=500, detail=result["error"])
    return {
        "status": "success",
        "message": "Email sent successfully.",
        "message_id": result.get("id"),
        "thread_id": result.get("threadId")
    }

@router.put("/{message_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_email_as_read(message_id: str, current_user: User = Depends(get_current_user)):
    """API endpoint to mark a specific email as read."""
    result = gmail_tools.mark_email_as_read.invoke({
        "user_id": current_user.id, "message_id": message_id
    })
    if "Error" in result:
        raise HTTPException(status_code=500, detail=result)
    return

# --- Admin Gmail Watcher Endpoints ---
# These can remain as they are, as they call a separate tool file.
@router.post("/watch", status_code=status.HTTP_200_OK)
def watch_gmail_inbox(current_user: User = Depends(get_current_user)):
    try:
        response = gmail_watcher.watch_gmail_inbox(user_id=current_user.id)
        return {"status": "success", "detail": "Gmail watch initiated.", "watch_data": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate Gmail watch: {e}")

@router.post("/unwatch", status_code=status.HTTP_200_OK)
def unwatch_gmail_inbox(current_user: User = Depends(get_current_user)):
    try:
        stop_success = gmail_watcher.stop_gmail_inbox_watch(user_id=current_user.id)
        if stop_success:
            return {"status": "success", "detail": "Gmail watch stopped."}
        else:
            raise HTTPException(status_code=500, detail="Failed to stop Gmail watch")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop Gmail watch: {e}")