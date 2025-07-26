from src.database import crud, database, models
from src.core import security # Needed for password verification in tests
import json # Needed for saving Google credentials data
import datetime # <-- NEW IMPORT: Explicitly import datetime
import time # For unique timestamps in emails

# Ensure the database and tables are created (and recreated if schema changed)
# This will also delete existing data from database.db, which is intended for this test.
database.create_database_and_tables()

# Get a database session for testing
db_session = database.SessionLocal()

def run_all_crud_tests():
    print("\n--- Running ALL CRUD Tests ---")

    # --- USER CRUD TESTS ---
    print("\n[TEST SECTION] User CRUD Operations...")

    # Test 1: Create a new user (with cleanup for repeated runs)
    print("\n  [TEST] Creating a new user...")
    user_email = "testuser@aibuddies.com"
    user_password = "SecurePassword123"
    
    # Clean up existing user and their associated data if they exist
    existing_user = crud.get_user_by_email(db_session, user_email)
    if existing_user:
        # Delete related Google Credentials
        user_creds = crud.get_google_credentials_by_user_id(db_session, existing_user.id)
        if user_creds:
            db_session.delete(user_creds)
            print(f"    - Cleaned up existing Google credentials for user: {user_email}")

        # Delete related Tasks
        for task in crud.get_all_tasks(db_session, existing_user.id):
            db_session.delete(task)
            print(f"    - Cleaned up existing task: {task.id}")
        
        # Delete related Notes
        for note in crud.get_all_notes(db_session, existing_user.id):
            db_session.delete(note)
            print(f"    - Cleaned up existing note: {note.key}")

        # Now delete the user
        db_session.delete(existing_user)
        db_session.commit() # Commit deletions
        print(f"    - Cleaned up existing user: {user_email}")
        
        # After deleting the user, it's good practice to close/reopen session for clean state
        # In a test, this can also be handled by deleting database.db before each run.
        # For simplicity, if database.db is deleted at the start, this cleanup is less critical,
        # but it's good to show how to handle it.
        
    # Create the new user
    new_user = crud.create_user(db_session, email=user_email, password=user_password)
    print(f"    - Created User: {new_user}")
    assert new_user.email == user_email
    assert security.verify_password(user_password, new_user.hashed_password)
    print("    ✅ User creation and password hash verification PASSED.")

    user_id = new_user.id
    
    # Test 2: Get user by email
    print("\n  [TEST] Getting user by email...")
    fetched_user_by_email = crud.get_user_by_email(db_session, user_email)
    print(f"    - Fetched User by Email: {fetched_user_by_email}")
    assert fetched_user_by_email.id == user_id
    print("    ✅ Get user by email PASSED.")

    # Test 3: Get user by ID
    print("\n  [TEST] Getting user by ID...")
    fetched_user_by_id = crud.get_user_by_id(db_session, user_id)
    print(f"    - Fetched User by ID: {fetched_user_by_id}")
    assert fetched_user_by_id.email == user_email
    print("    ✅ Get user by ID PASSED.")

    # --- GOOGLE CREDENTIALS CRUD TESTS ---
    print("\n[TEST SECTION] Google Credentials CRUD Operations...")

    # Example token data (simplified for testing)
    test_token_data = {
        "token": {"access_token": "example_access_token_123", "token_type": "Bearer"}, # Make this a dict to test json.dumps
        "refresh_token": "example_refresh_token_xyz",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "test_client_id.apps.googleusercontent.com",
        "client_secret": "test_client_secret",
        "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
        "expiry": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1) # <-- FIX: datetime object
    }
    
    # Test 4: Save new Google Credentials for the user
    print("\n  [TEST] Saving Google Credentials...")
    saved_creds = crud.save_google_credentials(db_session, user_id, test_token_data)
    print(f"    - Saved Credentials: {saved_creds}")
    assert saved_creds.user_id == user_id
    assert json.loads(saved_creds.token) == test_token_data['token'] # Ensure token is saved as JSON string
    assert saved_creds.refresh_token == test_token_data['refresh_token']
    print("    ✅ Google Credentials save (create) PASSED.")

    # Test 5: Update Google Credentials
    print("\n  [TEST] Updating Google Credentials...")
    updated_token_data = test_token_data.copy()
    updated_token_data['token'] = {"access_token": "updated_access_token_456", "token_type": "Bearer"}
    updated_token_data['scopes'] = ["https://www.googleapis.com/auth/gmail.modify"]
    updated_token_data['expiry'] = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2) # Ensure datetime object
    
    updated_creds = crud.save_google_credentials(db_session, user_id, updated_token_data)
    print(f"    - Updated Credentials: {updated_creds}")
    assert json.loads(updated_creds.token) == updated_token_data['token']
    assert updated_creds.scopes == ','.join(updated_token_data['scopes']) # Scopes are now comma-separated string
    print("    ✅ Google Credentials save (update) PASSED.")

    # Test 6: Get Google Credentials by user ID
    print("\n  [TEST] Getting Google Credentials by user ID...")
    fetched_creds = crud.get_google_credentials_by_user_id(db_session, user_id)
    print(f"    - Fetched Credentials: {fetched_creds}")
    assert fetched_creds.token == json.dumps(updated_token_data['token'])
    print("    ✅ Get Google Credentials by user ID PASSED.")

    # --- TASK CRUD TESTS (with user_id filtering) ---
    print("\n[TEST SECTION] Task CRUD Operations (User-Specific)...")
    
    # Test 7: Create tasks for the user
    print("\n  [TEST] Creating tasks for user...")
    task1 = crud.create_task(db_session, description="User task 1", user_id=user_id)
    task2 = crud.create_task(db_session, description="User task 2", user_id=user_id)
    print(f"    - Created Task 1: {task1}")
    print(f"    - Created Task 2: {task2}")
    assert task1.user_id == user_id
    assert task2.user_id == user_id
    print("    ✅ Task creation with user_id PASSED.")

    # Test 8: Get all tasks for the user
    print("\n  [TEST] Getting all tasks for user...")
    all_user_tasks = crud.get_all_tasks(db_session, user_id=user_id)
    print(f"    - Found {len(all_user_tasks)} tasks for user.")
    assert len(all_user_tasks) == 2
    for task in all_user_tasks:
        assert task.user_id == user_id
    print("    ✅ Get all tasks for user PASSED.")

    # Test 9: Get task by ID for the user
    print("\n  [TEST] Getting a specific task by ID for user...")
    fetched_task = crud.get_task_by_id(db_session, task_id=task1.id, user_id=user_id)
    print(f"    - Fetched Task: {fetched_task}")
    assert fetched_task.id == task1.id
    assert fetched_task.user_id == user_id
    print("    ✅ Get task by ID for user PASSED.")
    
    # Test 10: Try to get a task for wrong user (should be None)
    print("\n  [TEST] Getting task for wrong user (expected None)...")
    wrong_user_id = user_id + 100 # A user ID that doesn't exist or isn't assigned
    non_existent_task = crud.get_task_by_id(db_session, task_id=task1.id, user_id=wrong_user_id)
    print(f"    - Result for wrong user: {non_existent_task}")
    assert non_existent_task is None
    print("    ✅ Get task for wrong user PASSED.")

    # Test 11: Update task status for user
    print("\n  [TEST] Updating task status for user...")
    updated_task = crud.update_task_status(db_session, task_id=task1.id, user_id=user_id, new_status="completed")
    print(f"    - Updated Task: {updated_task}")
    assert updated_task.status == "completed"
    print("    ✅ Update task status for user PASSED.")

    # --- NOTE CRUD TESTS (with user_id filtering) ---
    print("\n[TEST SECTION] Note CRUD Operations (User-Specific)...")
    
    # Test 12: Create/Update notes for the user
    print("\n  [TEST] Creating/Updating notes for user...")
    note1 = crud.create_or_update_note(db_session, key="User Note 1", value="Content A", user_id=user_id)
    note2 = crud.create_or_update_note(db_session, key="User Note 2", value="Content B", user_id=user_id)
    print(f"    - Saved Note 1: {note1}")
    print(f"    - Saved Note 2: {note2}")
    assert note1.user_id == user_id
    assert note2.user_id == user_id
    print("    ✅ Note creation/update with user_id PASSED.")

    # Test 13: Get all notes for the user
    print("\n  [TEST] Getting all notes for user...")
    all_user_notes = crud.get_all_notes(db_session, user_id=user_id)
    print(f"    - Found {len(all_user_notes)} notes for user.")
    assert len(all_user_notes) == 2
    for note in all_user_notes:
        assert note.user_id == user_id
    print("    ✅ Get all notes for user PASSED.")

    # Test 14: Get a specific note by key for the user
    print("\n  [TEST] Getting a specific note by key for user...")
    fetched_note = crud.get_note_by_key(db_session, key="User Note 1", user_id=user_id)
    print(f"    - Fetched Note: {fetched_note}")
    assert fetched_note.key == "user note 1"
    assert fetched_note.user_id == user_id
    print("    ✅ Get note by key for user PASSED.")

    # Test 15: Try to get a note for wrong user (should be None)
    print("\n  [TEST] Getting note for wrong user (expected None)...")
    non_existent_note = crud.get_note_by_key(db_session, key="User Note 1", user_id=wrong_user_id)
    print(f"    - Result for wrong user: {non_existent_note}")
    assert non_existent_note is None
    print("    ✅ Get note for wrong user PASSED.")

    # Test 16: Delete a note for the user
    print("\n  [TEST] Deleting a note for user...")
    deleted = crud.delete_note_by_key(db_session, key="User Note 1", user_id=user_id)
    print(f"    - Deleted status: {deleted}")
    assert deleted is True
    print("    ✅ Delete note for user PASSED.")

    print("\n--- ALL CRUD Tests Completed Successfully! ---")

if __name__ == "__main__":
    try:
        run_all_crud_tests()
    finally:
        # IMPORTANT: Always close the session when you're done.
        db_session.close()