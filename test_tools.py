import asyncio
from src.agent.tools import calendar as calendar_tool
from src.agent.tools import gmail as gmail_tool
from src.agent.tools import gmail_watcher
from src.database import crud, database # Needed for user creation and creds retrieval
from src.core import security # Needed for user creation
import os
from dotenv import load_dotenv

# Load .env for mock credentials if running standalone
load_dotenv()

async def run_google_tool_tests():
    print("\n--- Running Refactored Google Tool Tests (Local) ---")

    # Ensure database is set up and we have a user with Google credentials
    database.create_database_and_tables()
    db_session = database.SessionLocal()
    
    # Create a test user (if not exists)
    test_email = "tool_test_user@aibuddies.com"
    test_password = "ToolTestPassword123"
    
    user = crud.get_user_by_email(db_session, test_email)
    if not user:
        user = crud.create_user(db_session, test_email, test_password)
        print(f"Created test user: {user.email} (ID: {user.id})")
    else:
        print(f"Using existing test user: {user.email} (ID: {user.id})")
    
    test_user_id = user.id

    # IMPORTANT: Manually populate Google Credentials for this user in your database
    # For a real test, you would run the full OAuth flow (like you did on Render)
    # against your local FastAPI server to save the credentials for 'tool_test_user@aibuddies.com'.
    # If you skip this, the tools will fail with "No Google credentials found".
    
    # As a fallback, try to retrieve credentials from DB to see if they exist
    creds_in_db = crud.get_google_credentials_by_user_id(db_session, test_user_id)
    if not creds_in_db:
        print("\n!!! WARNING !!!")
        print(f"No Google credentials found in DB for user ID {test_user_id}. Please perform the OAuth flow locally for this user:")
        print(f"1. Start your FastAPI server locally (python main.py)")
        print(f"2. Register and login 'tool_test_user@aibuddies.com' locally to get JWT.")
        print(f"3. Use 'curl -v -H \"Authorization: Bearer <JWT>\" http://127.0.0.1:8000/auth/google/login' to get Google Auth URL.")
        print(f"4. Paste URL into browser and complete Google authorization for 'tool_test_user@aibuddies.com'.")
        print("Skipping Google-backed tool tests as credentials are not available.")
        db_session.close()
        return


    try:
        # --- CALENDAR TOOL TEST ---
        print("\n[TEST] Fetching upcoming events...")
        events = await asyncio.get_running_loop().run_in_executor(
            None, calendar_tool.fetch_upcoming_events, test_user_id, 2
        )
        print(f"  - Found {len(events)} events.")
        if events:
            print(f"    - First event: {events[0].get('summary')}")
        print("  ✅ Fetch upcoming events PASSED (if credentials valid).")

        # Create a new event (test parsing to ISO format manually for now)
        print("\n[TEST] Creating a new event...")
        now = datetime.datetime.now(datetime.timezone.utc)
        start_time = (now + datetime.timedelta(days=1, hours=9)).isoformat()
        end_time = (now + datetime.timedelta(days=1, hours=10)).isoformat()
        
        new_event = await asyncio.get_running_loop().run_in_executor(
            None, calendar_tool.create_new_event, test_user_id, 
            "Test Aura Event", start_time, end_time, 
            "Created by AIBuddies automation test", "Virtual Meeting"
        )
        print(f"  - New event created: {new_event.get('htmlLink')}")
        print("  ✅ Create new event PASSED (if credentials valid).")

        # --- GMAIL TOOL TEST ---
        print("\n[TEST] Fetching unread emails...")
        unread_emails = await asyncio.get_running_loop().run_in_executor(
            None, gmail_tool.fetch_unread_emails, test_user_id, 2
        )
        print(f"  - Found {len(unread_emails)} unread emails.")
        if unread_emails:
            print(f"    - First email: {unread_emails[0].get('subject')} from {unread_emails[0].get('sender')}")
        print("  ✅ Fetch unread emails PASSED (if credentials valid).")
        
        if unread_emails:
            print(f"\n[TEST] Getting body of first unread email: {unread_emails[0]['id']}")
            email_body = await asyncio.get_running_loop().run_in_executor(
                None, gmail_tool.get_email_body, test_user_id, unread_emails[0]['id']
            )
            print(f"  - Email body (first 100 chars): {email_body[:100] if email_body else 'No body found'}")
            print("  ✅ Get email body PASSED (if credentials valid).")
            
            print(f"\n[TEST] Marking first unread email as read: {unread_emails[0]['id']}")
            await asyncio.get_running_loop().run_in_executor(
                None, gmail_tool.mark_message_as_read, test_user_id, unread_emails[0]['id']
            )
            print("  ✅ Mark message as read PASSED (if credentials valid).")

        # --- GMAIL WATCHER TOOL TEST (requires GCP project/topic setup) ---
        print("\n[TEST] Attempting to initiate Gmail Watch...")
        if config.GCP_PROJECT_ID == "YOUR_GCP_PROJECT_ID_HERE" or config.GCP_PUBSUB_TOPIC_ID == "YOUR_GCP_PUBSUB_TOPIC_ID_HERE":
            print("  - Skipping Gmail Watcher tests: GCP_PROJECT_ID or GCP_PUBSUB_TOPIC_ID not configured in .env.")
        else:
            try:
                watch_response = await asyncio.get_running_loop().run_in_executor(
                    None, gmail_watcher.watch_gmail_inbox, test_user_id
                )
                print(f"  - Gmail Watch initiated: {watch_response}")
                print("  ✅ Gmail Watcher initiated PASSED.")
                
                print("\n[TEST] Attempting to stop Gmail Watch...")
                stop_success = await asyncio.get_running_loop().run_in_executor(
                    None, gmail_watcher.stop_gmail_inbox_watch, test_user_id
                )
                print(f"  - Gmail Watch stopped: {stop_success}")
                print("  ✅ Gmail Watcher stopped PASSED.")

            except Exception as e:
                print(f"  ❌ Gmail Watcher test FAILED: {e}")


    except Exception as e:
        print(f"\n❌ A Google-backed tool test failed due to an error: {e}")
        # This will catch errors like "No Google credentials found" or API errors
    finally:
        db_session.close()
        print("\n--- Google Tool Tests Complete ---")

if __name__ == "__main__":
    from src.core import config # Load config to ensure env vars are picked up
    asyncio.run(run_google_tool_tests())