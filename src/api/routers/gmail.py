from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from src.database.models import GmailMessageResponse, User, GmailSendRequest
from src.database.database import get_db
from src.api.dependencies import get_current_user # Our authentication dependency
from src.agent.tools import gmail as gmail_tool # Our refactored gmail tool
from src.agent.tools import gmail_watcher # For watch/unwatch (admin)
from googleapiclient.errors import HttpError

router = APIRouter(
    prefix="/gmail",
    tags=["Gmail"]
)

@router.get("/unread", response_model=List[GmailMessageResponse])
def get_unread_emails(
    db: Session = Depends(get_db), # Not directly used but good practice
    current_user: User = Depends(get_current_user), # Requires authentication
    max_results: int = 5
):
    """
    Retrieve a list of unread emails for the authenticated user.
    """
    print(f"API: Fetching unread emails for user ID: {current_user.id}")
    try:
        emails = gmail_tool.fetch_unread_emails(user_id=current_user.id, max_results=max_results)
        return [
            GmailMessageResponse(
                id=email.get('id'),
                subject=email.get('subject'),
                sender=email.get('sender'),
                # Add other fields if desired from the full email metadata, or set default to None
            ) for email in emails
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch unread emails: {e}"
        )

@router.get("/{message_id}/body")
def get_email_body(
    message_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve the plain text body of a specific email message for the authenticated user.
    """
    print(f"API: Getting email body for message {message_id} for user ID: {current_user.id}")
    try:
        email_body = gmail_tool.get_email_body(user_id=current_user.id, message_id=message_id)
        if email_body is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Email body for message ID '{message_id}' not found or is not plain text."
            )
        return {"message_id": message_id, "body": email_body}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve email body: {e}"
        )

@router.put("/{message_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_email_as_read(
    message_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marks a specific email message as read for the authenticated user.
    """
    print(f"API: Marking message {message_id} as read for user ID: {current_user.id}")
    try:
        gmail_tool.mark_message_as_read(user_id=current_user.id, message_id=message_id)
        return # 204 No Content response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark email as read: {e}"
        )

# --- Admin Gmail Watcher Endpoints (require specific GCP setup) ---
# These would typically be in an /admin router, but for now we put them here for simplicity.

@router.post("/watch", status_code=status.HTTP_200_OK)
def watch_gmail_inbox(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Initiates real-time Gmail push notifications for the authenticated user.
    Requires Google Cloud Pub/Sub setup and correct GCP_PROJECT_ID/GCP_PUBSUB_TOPIC_ID in .env.
    """
    print(f"API: Attempting to watch Gmail inbox for user ID: {current_user.id}")
    try:
        response = gmail_watcher.watch_gmail_inbox(user_id=current_user.id)
        if response:
            return {"status": "success", "detail": "Gmail watch initiated.", "watch_data": response}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initiate Gmail watch for unknown reason."
            )
    except Exception as e:
        print(f"API ERROR: Failed to watch Gmail inbox for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate Gmail watch: {e}"
        )

@router.post("/unwatch", status_code=status.HTTP_200_OK)
def unwatch_gmail_inbox(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Stops real-time Gmail push notifications for the authenticated user.
    """
    print(f"API: Attempting to stop Gmail watch for user ID: {current_user.id}")
    try:
        stop_success = gmail_watcher.stop_gmail_inbox_watch(user_id=current_user.id)
        if stop_success:
            return {"status": "success", "detail": "Gmail watch stopped."}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to stop Gmail watch for unknown reason."
            )
    except Exception as e:
        print(f"API ERROR: Failed to stop Gmail watch for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop Gmail watch: {e}"
        )
@router.post("/send", status_code=status.HTTP_201_CREATED)
def send_new_email(
    email_data: GmailSendRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Compose and send a new email from the authenticated user's account.
    """
    print(f"API: Received request to send email for user ID: {current_user.id}")
    try:
        sent_message = gmail_tool.send_email(
            user_id=current_user.id,
            to=email_data.to,
            subject=email_data.subject,
            body=email_data.body
        )
        if not sent_message:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send email for an unknown reason."
            )
        
        # Return a confirmation response
        return {
            "status": "success",
            "message": "Email sent successfully.",
            "message_id": sent_message.get("id"),
            "thread_id": sent_message.get("threadId")
        }
    except HttpError as e:
        # Provide a more specific error if permissions are denied
        if e.resp.status == 403:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Failed to send email: Permission denied. The 'gmail.send' scope may be missing or revoked."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email due to a Google API error: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while sending email: {e}"
        )