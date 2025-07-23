# File: src/agent/tools/gmail_watcher.py

from googleapiclient.errors import HttpError
from src.core.gcp_auth import build_google_service
import json

# Define constants for the Pub/Sub setup
# IMPORTANT: Replace these with your actual Project ID and Topic ID
# You can find your Project ID in the Google Cloud Console Dashboard.
# The Topic ID is what you named it (e.g., 'aura-gmail-notifications').
GCP_PROJECT_ID = "aura-466616" # <-- REPLACE THIS
GCP_PUBSUB_TOPIC_ID = "aura-gmail-notifications" # <-- REPLACE THIS IF YOU NAMED IT DIFFERENTLY

def watch_gmail_inbox() -> dict | None:
    """
    Tells the Gmail API to send push notifications to a Pub/Sub topic
    whenever there's a change in the user's inbox.
    
    Returns:
        A dictionary with watch details (e.g., expiration, historyId) on success.
    """
    try:
        service = build_google_service('gmail', 'v1')
        
        # The request body for the watch API
        request_body = {
            'topicName': f'projects/{GCP_PROJECT_ID}/topics/{GCP_PUBSUB_TOPIC_ID}'
            # You can also add 'labelIds': ['INBOX'] if you only want inbox changes
        }
        
        # Call the watch API
        response = service.users().watch(userId='me', body=request_body).execute()
        
        print(f"Gmail watch initiated successfully: {response}")
        return response
    except HttpError as error:
        print(f"An HTTP error occurred while watching Gmail inbox: {error.resp.status}")
        print(f"Error details: {error._get_reason()}")
        raise error
    except Exception as e:
        print(f"An unexpected error occurred while watching Gmail inbox: {e}")
        raise e

def stop_gmail_inbox_watch() -> bool:
    """
    Stops sending push notifications for the user's Gmail inbox.
    
    Returns:
        True on successful stop, False otherwise.
    """
    try:
        service = build_google_service('gmail', 'v1')
        
        # Call the stop API
        response = service.users().stop(userId='me').execute()
        
        print(f"Gmail watch stopped successfully: {response}")
        # The stop API usually returns an empty dictionary on success.
        return True
    except HttpError as error:
        print(f"An HTTP error occurred while stopping Gmail inbox watch: {error.resp.status}")
        print(f"Error details: {error._get_reason()}")
        raise error
    except Exception as e:
        print(f"An unexpected error occurred while stopping Gmail inbox watch: {e}")
        raise e