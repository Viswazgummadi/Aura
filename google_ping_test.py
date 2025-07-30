# google_ping_test.py

import httpx
import sys

# This is the Google server our main app is trying to talk to.
TOKEN_URL = "https://oauth2.googleapis.com/token"

print("--- Google Connection Test ---")
print(f"Python version: {sys.version}")
print(f"httpx version: {httpx.__version__}")
print(f"Target URL: {TOKEN_URL}")
print("\nAttempting to connect...")

try:
    # We will try to make the request with a 10-second timeout.
    # If the network is blocked, this will hang for 10 seconds then crash.
    # If the network is open, this will complete almost instantly.
    with httpx.Client() as client:
        response = client.post(TOKEN_URL, timeout=10.0)

    print("\n✅ SUCCESS: Connection complete!")
    print(f"Google's server responded with status code: {response.status_code}")
    print("This means your network connection is NOT the problem.")
    print("The response body (this is a normal error from Google):")
    print(response.text)

except httpx.TimeoutException:
    print("\n❌ FAILURE: Connection timed out after 10 seconds.")
    print("This is the 'infinite loading' problem.")
    print("This strongly suggests something on your machine or network is blocking Python from connecting to Google.")

except httpx.ConnectError as e:
    print(f"\n❌ FAILURE: A connection error occurred: {e}")
    print("This also suggests a firewall or network issue.")

except Exception as e:
    print(f"\n❌ An unexpected error occurred: {e}")