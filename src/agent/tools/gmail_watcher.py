from googleapiclient.errors import HttpError
from src.core.gcp_auth import build_google_service
from src.core import config # <-- NEW IMPORT: for GCP_PROJECT_ID and GCP_PUBSUB_TOPIC_ID

# These constants should be loaded from config.py from now on
# GCP_PROJECT_ID = "aura-466616" 
# GCP_PUBSUB_TOPIC_ID = "aura-gmail-notifications" 

def watch_gmail_inbox(user_id: int) -> dict | None: # <-- NEW: user_id argument
    """
    Tells the Gmail API to send push notifications to a Pub/Sub topic
    whenever there's a change in the user's inbox.
    
    Args:
        user_id (int): The ID of the AIBuddies user whose Gmail to watch.

    Returns:
        A dictionary with watch details (e.g., expiration, historyId) on success.
    """
    print(f"TOOL: watch_gmail_inbox called for user ID: {user_id}")
    try:
        # Pass the user_id to build_google_service
        service = build_google_service('gmail', 'v1', user_id=user_id)
        
        request_body = {
            'topicName': f'projects/{config.GCP_PROJECT_ID}/topics/{config.GCP_PUBSUB_TOPIC_ID}' # <-- Use config
        }
        
        response = service.users().watch(userId='me', body=request_body).execute()
        
        print(f"Gmail watch initiated successfully for user {user_id}: {response}")
        return response
    except HttpError as error:
        print(f"An HTTP error occurred while watching Gmail inbox for user {user_id}: {error.resp.status}")
        print(f"Error details: {error._get_reason()}")
        raise error
    except Exception as e:
        print(f"An unexpected error occurred while watching Gmail inbox for user {user_id}: {e}")
        raise e

def stop_gmail_inbox_watch(user_id: int) -> bool: # <-- NEW: user_id argument
    """
    Stops sending push notifications for the user's Gmail inbox.
    
    Args:
        user_id (int): The ID of the AIBuddies user whose Gmail watch to stop.

    Returns:
        True on successful stop, False otherwise.
    """
    print(f"TOOL: stop_gmail_inbox_watch called for user ID: {user_id}")
    try:
        # Pass the user_id to build_google_service
        service = build_google_service('gmail', 'v1', user_id=user_id)
        
        response = service.users().stop(userId='me').execute()
        
        print(f"Gmail watch stopped successfully for user {user_id}: {response}")
        return True
    except HttpError as error:
        print(f"An HTTP error occurred while stopping Gmail inbox watch for user {user_id}: {error.resp.status}")
        print(f"Error details: {error._get_reason()}")
        raise error
    except Exception as e:
        print(f"An unexpected error occurred while stopping Gmail inbox watch for user {user_id}: {e}")
        raise e