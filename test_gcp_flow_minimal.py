import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from google_auth_oauthlib.flow import Flow
import datetime
from dotenv import load_dotenv

# Load environment variables for configuration
load_dotenv()

# --- Configuration (from your .env) ---
# Use your actual Client ID/Secret/Redirect URI from your .env for this test
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "YOUR_GOOGLE_CLIENT_ID_HERE.apps.googleusercontent.com")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "YOUR_GOOGLE_CLIENT_SECRET_HERE")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/auth/google/callback")

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.settings.basic"
]

# This will be passed to run_in_executor
def _fetch_token_target(flow_instance: Flow, auth_code: str):
    print(f"DEBUG: Inside _fetch_token_target, calling flow_instance.fetch_token({auth_code[:10]}...)")
    # This is the line that causes the error.
    flow_instance.fetch_token(auth_code)
    print("DEBUG: fetch_token completed in thread.")
    return flow_instance.credentials

async def main():
    print("--- Starting Debug Test for Flow.fetch_token ---")

    if not all([CLIENT_ID, CLIENT_SECRET, REDIRECT_URI]):
        print("CRITICAL: Google OAuth environment variables not set in .env. Please configure them.")
        return

    # IMPORTANT: You need a REAL, ONE-TIME-USE authorization code here.
    # Get it by starting your FastAPI app, getting the /auth/google/login URL from curl,
    # pasting that URL into your browser, completing Google auth,
    # and then copying the 'code' query parameter from the browser's redirect URL.
    # This code is only valid for a few seconds/minutes after Google issues it.
    live_auth_code = "PASTE_YOUR_LIVE_AUTH_CODE_HERE"
    live_state = "PASTE_YOUR_LIVE_STATE_HERE" # State is not used by fetch_token directly, but useful for context

    if live_auth_code == "PASTE_YOUR_LIVE_AUTH_CODE_HERE":
        print("\nWARNING: Please update 'live_auth_code' and 'live_state' in this script with actual values.")
        print("To get these, run your FastAPI app, trigger the /auth/google/login flow,")
        print("complete Google authorization in your browser, and copy the 'state' and 'code' from the URL your browser redirects to.")
        return

    # 1. Create the Flow object on the main thread
    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    # 2. Use ThreadPoolExecutor directly to mimic run_in_executor's behavior
    executor = ThreadPoolExecutor()
    print("DEBUG: Submitting _fetch_token_target to executor...")
    
    # We pass the flow instance and the auth_code as direct arguments.
    # If the error still occurs here, it's definitely how flow.fetch_token is compiled/used.
    future = loop.run_in_executor(executor, _fetch_token_target, flow, live_auth_code)
    
    try:
        creds = await future
        print(f"\n✅ TEST SUCCESS: Credentials fetched via _fetch_token_target. Access Token: {creds.token[:10]}...")
        print(f"Refresh Token present: {creds.refresh_token is not None}")
        print(f"Expiry: {creds.expiry}")
    except Exception as e:
        print(f"\n❌ TEST FAILED: An error occurred during token exchange: {e}")
    finally:
        executor.shutdown(wait=True) # Ensure the thread pool shuts down

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())