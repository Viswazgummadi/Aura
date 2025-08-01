#database/crud.py

import uuid
import datetime
import json
from typing import List, Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session
import secrets
from . import models
from src.core.security import get_password_hash
from src.core.config import DateTimeEncoder # <-- NEW IMPORT: Our custom JSON encoder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
# --- User CRUD Functions (existing, no changes) ---
def get_user_by_email(db: Session, email: str) -> models.User | None:
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_id(db: Session, user_id: int) -> models.User | None:
    return db.query(models.User).filter(models.User.id == user_id).first()

def create_user(db: Session, email: str, password: str) -> models.User:
    hashed_password = get_password_hash(password)
    db_user = models.User(email=email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- Google Credentials CRUD Functions (UPDATED) ---

def get_google_credentials_by_user_id(db: Session, user_id: int) -> models.GoogleCredentials | None:
    return db.query(models.GoogleCredentials).filter(models.GoogleCredentials.user_id == user_id).first()

def save_google_credentials(
    db: Session,
    user_id: int,
    token_data: dict # This dict should contain 'access_token', 'refresh_token', 'expiry' (as datetime object!), etc.
) -> models.GoogleCredentials:
    """
    Saves or updates Google credentials for a user.
    'token_data' should be a dictionary containing the full set of token info.
    The expiry field in token_data MUST be a datetime object.
    """
    db_creds = get_google_credentials_by_user_id(db, user_id)
    
    # Store the entire token_data dictionary as a JSON string using our custom encoder
    token_json_to_save = json.dumps(token_data, cls=DateTimeEncoder) # <-- THE FIX IS HERE: Use custom encoder
    print("Saving token_json_to_save:", token_json_to_save)

    
    # For scopes, ensure it's a comma-separated string if it comes as a list
    scopes_str = ','.join(token_data.get('scopes', [])) if isinstance(token_data.get('scopes'), list) else token_data.get('scopes', '')

    if db_creds:
        # Update existing credentials
        db_creds.token = token_json_to_save
        db_creds.refresh_token = token_data.get('refresh_token') # refresh_token can be None initially
        db_creds.token_uri = token_data.get('token_uri')
        db_creds.client_id = token_data.get('client_id')
        db_creds.client_secret = token_data.get('client_secret')
        db_creds.scopes = scopes_str
        db_creds.expiry = token_data.get('expiry') # This expects a datetime object (from gcp_auth.py)
        db_creds.google_email = token_data.get('google_email') # <-- ADD THIS LINE

    else:
        # Create new credentials
        db_creds = models.GoogleCredentials(
            user_id=user_id,
            token=token_json_to_save,
            refresh_token=token_data.get('refresh_token'),
            token_uri=token_data.get('token_uri'),
            client_id=token_data.get('client_id'),
            client_secret=token_data.get('client_secret'),
            scopes=scopes_str,
            expiry=token_data.get('expiry'),
            google_email=token_data.get('google_email') # <-- ADD THIS LINE
        )
        db.add(db_creds)
    
    db.commit()
    db.refresh(db_creds)
    return db_creds

def delete_google_credentials_by_user_id(db: Session, user_id: int) -> bool:
    db_creds = get_google_credentials_by_user_id(db, user_id)
    if db_creds:
        db.delete(db_creds)
        db.commit()
        return True
    return False

# --- NEW: OAuth State CRUD Functions (existing, no changes) ---
def create_oauth_state(db: Session, user_id: int) -> models.OAuthState:
    state_value = secrets.token_urlsafe(32)
    db_oauth_state = models.OAuthState(user_id=user_id, state_value=state_value)
    db.add(db_oauth_state)
    db.commit()
    db.refresh(db_oauth_state)
    return db_oauth_state

def get_oauth_state_by_value(db: Session, state_value: str) -> models.OAuthState | None:
    return db.query(models.OAuthState).filter(models.OAuthState.state_value == state_value).first()

def delete_oauth_state(db: Session, state_value: str) -> bool:
    db_oauth_state = get_oauth_state_by_value(db, state_value)
    if db_oauth_state:
        db.delete(db_oauth_state)
        db.commit()
        return True
    return False

# ADD THIS NEW BLOCK IN ITS PLACE
# --- UPDATED Task CRUD Functions ---

def get_task_by_id(db: Session, task_id: str, user_id: int) -> models.Task | None:
    """Retrieves a single task by its unique ID, ensuring it belongs to the user."""
    return db.query(models.Task).filter(models.Task.id == task_id, models.Task.user_id == user_id).first()

def get_all_tasks(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    priority: Optional[str] = None
) -> list[models.Task]:
    """
    Retrieves top-level tasks for a user, with optional filtering and intelligent sorting.
    Sub-tasks will be nested within their parents and not returned at the top level.
    """
    # --- THIS IS THE FIX ---

    # 1. Start with the base query. This ALWAYS runs.
    query = db.query(models.Task).filter(models.Task.user_id == user_id)

    # 2. Add the filter to only get top-level tasks. This ALWAYS runs.
    query = query.filter(models.Task.parent_id == None)

    # 3. Incrementally add the optional filters if they exist.
    if status:
        query = query.filter(models.Task.status == status)
    if priority:
        query = query.filter(models.Task.priority == priority)

    # 4. Apply sorting and limits to the final, constructed query.
    return (
        query.order_by(
            models.Task.status.desc(),
            models.Task.due_date.asc().nullslast(),
            models.Task.priority.desc()
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

def create_task(db: Session, task: models.TaskCreate, user_id: int) -> models.Task:
    """Creates a new task, now with optional priority and due_date."""
    # We'll need a unique ID for the task, let's generate one.
    # We need to import uuid at the top of the file for this.
    new_task_id = str(uuid.uuid4())[:8]
    
    # Unpack the Pydantic model into the SQLAlchemy model
    db_task = models.Task(
        id=new_task_id,
        user_id=user_id,
        **task.model_dump(exclude_unset=True) # Use exclude_unset to respect defaults
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def create_task_batch(db: Session, tasks: list[models.TaskCreate], user_id: int) -> list[models.Task]:
    """
    Creates multiple tasks in a single database transaction.
    This is more efficient than creating them one by one.
    """
    db_tasks = []
    for task_data in tasks:
        # Generate a unique ID for each new task
        new_task_id = str(uuid.uuid4())[:8]
        
        # Create the SQLAlchemy model instance
        db_task = models.Task(
            id=new_task_id,
            user_id=user_id,
            **task_data.model_dump(exclude_unset=True) # Unpack data from Pydantic model
        )
        db_tasks.append(db_task)

    # Use db.add_all() to add all new task objects to the session
    db.add_all(db_tasks)
    db.commit()
    
    # We don't call db.refresh() on a list. The data is already correct.
    return db_tasks


def update_task(db: Session, task_id: str, task_update: models.TaskUpdate, user_id: int) -> models.Task | None:
    """A flexible update function for any task attribute."""
    db_task = get_task_by_id(db, task_id, user_id)
    if db_task:
        # THE FIX: Get the update data, excluding any fields that were not set.
        # This ensures we only update the attributes the user actually provided.
        update_data = task_update.model_dump(exclude_unset=True)
        
        for key, value in update_data.items():
            setattr(db_task, key, value)
            
        db.commit()
        db.refresh(db_task)
    return db_task

def delete_task_by_id(db: Session, task_id: str, user_id: int) -> bool:
    """
    Deletes a task from the database by its ID, ensuring it belongs to the user.

    Returns:
        True if the task was found and deleted, False otherwise.
    """
    # First, get the task to make sure it exists and belongs to the user
    db_task = get_task_by_id(db, task_id=task_id, user_id=user_id)
    
    if db_task:
        db.delete(db_task)
        db.commit()
        return True
        
    return False
# --- Note CRUD Functions (existing, no changes) ---
def get_note_by_id(db: Session, note_id: int, user_id: int) -> models.Note | None:
    """Retrieves a single note by its unique ID, ensuring it belongs to the user."""
    return db.query(models.Note).filter(models.Note.id == note_id, models.Note.user_id == user_id).first()

def get_all_notes(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> list[models.Note]:
    """Retrieves all notes for a specific user, ordered by the most recently updated."""
    return db.query(models.Note).filter(models.Note.user_id == user_id).order_by(models.Note.updated_at.desc()).offset(skip).limit(limit).all()

def create_note(db: Session, note: models.NoteCreate, user_id: int) -> models.Note:
    """Creates a new note in the database."""
    # We use **note.model_dump() to unpack the Pydantic model into keyword arguments
    db_note = models.Note(**note.model_dump(), user_id=user_id)
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note

def update_note(db: Session, note_id: int, note_update: models.NoteUpdate, user_id: int) -> models.Note | None:
    """Updates a note's title or content. Only updates fields that are provided."""
    db_note = get_note_by_id(db, note_id=note_id, user_id=user_id)
    if db_note:
        # Get the update data, excluding any None values so we only update what's provided
        update_data = note_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_note, key, value)
        
        # Manually set the updated_at timestamp
        db_note.updated_at = datetime.datetime.now(datetime.timezone.utc)
        db.commit()
        db.refresh(db_note)
    return db_note

def delete_note_by_id(db: Session, note_id: int, user_id: int) -> bool:
    """Deletes a note from the database by its ID."""
    db_note = get_note_by_id(db, note_id=note_id, user_id=user_id)
    if db_note:
        db.delete(db_note)
        db.commit()
        return True
    return False
# --- Tag CRUD Functions ---

def get_or_create_tag(db: Session, tag_name: str) -> models.Tag:
    """
    Efficiently retrieves a tag by its name if it exists,
    or creates it if it does not. Prevents duplicate tags.
    """
    # Normalize tag name to lowercase to prevent duplicates like "Work" and "work"
    normalized_name = tag_name.lower().strip()
    db_tag = db.query(models.Tag).filter(models.Tag.name == normalized_name).first()
    if not db_tag:
        db_tag = models.Tag(name=normalized_name)
        db.add(db_tag)
        db.commit()
        db.refresh(db_tag)
    return db_tag

def add_tag_to_note(db: Session, note_id: int, tag_name: str, user_id: int) -> models.Note | None:
    """Adds a tag to a specific note, creating the tag if necessary."""
    db_note = get_note_by_id(db, note_id=note_id, user_id=user_id)
    if db_note:
        db_tag = get_or_create_tag(db, tag_name=tag_name)
        # Check if the tag is not already associated with the note
        if db_tag not in db_note.tags:
            db_note.tags.append(db_tag)
            db.commit()
            db.refresh(db_note)
    return db_note

def remove_tag_from_note(db: Session, note_id: int, tag_id: int, user_id: int) -> models.Note | None:
    """Removes a tag from a specific note."""
    db_note = get_note_by_id(db, note_id=note_id, user_id=user_id)
    db_tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
    
    if db_note and db_tag and db_tag in db_note.tags:
        db_note.tags.remove(db_tag)
        db.commit()
        db.refresh(db_note)
        return db_note
    return None

def get_notes_by_tag_name(db: Session, tag_name: str, user_id: int) -> list[models.Note]:
    """Retrieves all notes for a user that are associated with a specific tag."""
    normalized_name = tag_name.lower().strip()
    return (
        db.query(models.Note)
        .join(models.Note.tags)
        .filter(models.Tag.name == normalized_name, models.Note.user_id == user_id)
        .all()
    )
def get_or_create_provider(db: Session, provider_name: str) -> models.LLMProvider:
    provider = db.query(models.LLMProvider).filter(models.LLMProvider.name == provider_name.lower()).first()
    if not provider:
        provider = models.LLMProvider(name=provider_name.lower())
        db.add(provider)
        db.commit()
        db.refresh(provider)
    return provider

def get_provider_by_name(db: Session, provider_name: str) -> models.LLMProvider | None:
    return db.query(models.LLMProvider).filter(models.LLMProvider.name == provider_name.lower()).first()

# --- API Key Functions ---
def add_api_key(db: Session, provider_name: str, key: str) -> models.APIKey:
    provider = get_or_create_provider(db, provider_name)
    db_key = models.APIKey(key=key, provider_id=provider.id)
    db.add(db_key)
    db.commit()
    db.refresh(db_key)
    return db_key

def get_next_api_key(db: Session, provider_name: str) -> models.APIKey | None:
    """
    This is the core logic for key rotation. It fetches the least recently used,
    active key for a given provider, and updates its last_used timestamp.
    This ensures we cycle through keys, distributing the load.
    """
    provider = get_provider_by_name(db, provider_name)
    if not provider:
        return None
        
    # Find the active key that was used the longest time ago
    db_key = (
        db.query(models.APIKey)
        .filter(models.APIKey.provider_id == provider.id, models.APIKey.is_active == True)
        .order_by(models.APIKey.last_used.asc())
        .first()
    )
    
    if db_key:
        # Update its timestamp to now, so it goes to the back of the line
        db_key.last_used = datetime.datetime.now(datetime.timezone.utc)
        db.commit()
        db.refresh(db_key)
        
    return db_key

def deactivate_api_key(db: Session, key_id: int) -> models.APIKey | None:
    db_key = db.query(models.APIKey).filter(models.APIKey.id == key_id).first()
    if db_key:
        db_key.is_active = False
        db.commit()
        db.refresh(db_key)
    return db_key

# --- LLM Model Functions ---
def add_llm_model(db: Session, provider_name: str, model_name: str) -> models.LLMModel:
    provider = get_or_create_provider(db, provider_name)
    db_model = models.LLMModel(name=model_name, provider_id=provider.id)
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model

def set_active_llm_model(db: Session, model_name: str) -> models.LLMModel | None:
    """
    Sets a specific model as active and deactivates all other models.
    Ensures that only one model is the "default" for the agent.
    """
    # First, deactivate all models
    db.query(models.LLMModel).update({"is_active": False})
    
    # Then, find and activate the desired model
    db_model = db.query(models.LLMModel).filter(models.LLMModel.name == model_name).first()
    if db_model:
        db_model.is_active = True
        db.commit()
        db.refresh(db_model)
    else:
        # If the model wasn't found, roll back the deactivation
        db.rollback()
    return db_model

def get_active_llm_model(db: Session) -> models.LLMModel | None:
    """Retrieves the currently active LLM for the agent to use."""
    return db.query(models.LLMModel).filter(models.LLMModel.is_active == True).first()
def update_user_watch_history_id(db: Session, user_id: int, new_history_id: str):
    """Updates the last processed historyId for a user's Gmail watch."""
    creds = get_google_credentials_by_user_id(db, user_id)
    if creds:
        creds.watch_history_id = new_history_id
        db.commit()
def add_chat_message(db: Session, session_id: str, message_json_dict: dict, user_id: int) -> models.ChatMessage:
    """Adds a new chat message to the database."""
    db_message = models.ChatMessage(
        session_id=session_id,
        # --- THIS IS THE FIX ---
        # Convert the dictionary to a JSON string before saving
        message=json.dumps(message_json_dict),
        user_id=user_id
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def get_chat_history(db: Session, session_id: str, user_id: int) -> list[models.ChatMessage]:
    """Retrieves all messages for a given session, ordered by time."""
    return (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session_id, models.ChatMessage.user_id == user_id)
        .order_by(models.ChatMessage.timestamp.asc())
        .all()
    )

def get_user_by_google_email(db: Session, google_email: str) -> models.User | None:
    """Finds a user by their linked Google account email."""
    # This query joins the tables to find the user associated with the Google credential
    return (
        db.query(models.User)
        .join(models.GoogleCredentials)
        .filter(models.GoogleCredentials.google_email == google_email)
        .first()
    )
    
def search_notes(db: Session, query: str, user_id: int) -> list[models.Note]:
    """
    Searches for notes belonging to a user where the query string is found
    in either the title or the content, case-insensitively.
    """
    search_query = f"%{query}%"
    return (
        db.query(models.Note)
        .filter(
            models.Note.user_id == user_id,
            or_(
                models.Note.title.ilike(search_query),
                models.Note.content.ilike(search_query)
            )
        )
        .all()
    )
def link_note_to_task(db: Session, note_id: int, task_id: str, user_id: int) -> models.Note | None:
    """Adds an association between a note and a task, ensuring both belong to the user."""
    # Retrieve the note and task, ensuring they belong to the current user
    db_note = get_note_by_id(db, note_id=note_id, user_id=user_id)
    db_task = get_task_by_id(db, task_id=task_id, user_id=user_id)
    
    if db_note and db_task:
        # Check if the link already exists to avoid duplicates
        if db_task not in db_note.tasks:
            db_note.tasks.append(db_task)
            db.commit()
            db.refresh(db_note)
        return db_note
    return None

def unlink_note_from_task(db: Session, note_id: int, task_id: str, user_id: int) -> models.Note | None:
    """Removes an association between a note and a task."""
    db_note = get_note_by_id(db, note_id=note_id, user_id=user_id)
    db_task = get_task_by_id(db, task_id=task_id, user_id=user_id)
    
    if db_note and db_task:
        # Check if the link exists before trying to remove it
        if db_task in db_note.tasks:
            db_note.tasks.remove(db_task)
            db.commit()
            db.refresh(db_note)
        return db_note
    return None
async def create_oauth_state_async(db: AsyncSession, user_id: int) -> models.OAuthState:
    state_value = secrets.token_urlsafe(32)
    db_oauth_state = models.OAuthState(user_id=user_id, state_value=state_value)
    db.add(db_oauth_state)
    await db.commit()
    await db.refresh(db_oauth_state)
    return db_oauth_state

async def get_oauth_state_by_value_async(db: AsyncSession, state_value: str) -> models.OAuthState | None:
    result = await db.execute(select(models.OAuthState).filter(models.OAuthState.state_value == state_value))
    return result.scalars().first()

async def delete_oauth_state_async(db: AsyncSession, state_value: str) -> bool:
    db_oauth_state = await get_oauth_state_by_value_async(db, state_value)
    if db_oauth_state:
        await db.delete(db_oauth_state)
        await db.commit()
        return True
    return False

async def save_google_credentials_async(db: AsyncSession, user_id: int, token_data: dict) -> models.GoogleCredentials:
    result = await db.execute(select(models.GoogleCredentials).filter(models.GoogleCredentials.user_id == user_id))
    db_creds = result.scalars().first()
    
    token_json_to_save = json.dumps(token_data, cls=DateTimeEncoder)
    scopes_str = ','.join(token_data.get('scopes', []))

    if db_creds:
        db_creds.token = token_json_to_save
        db_creds.access_token = token_data.get('access_token')
        db_creds.refresh_token = token_data.get('refresh_token')
        db_creds.expiry = token_data.get('expiry')
        db_creds.google_email = token_data.get('google_email')
    else:
        db_creds = models.GoogleCredentials(
            user_id=user_id,
            token=token_json_to_save,
            access_token=token_data.get('access_token'),
            refresh_token=token_data.get('refresh_token'),
            token_uri=token_data.get('token_uri'),
            client_id=token_data.get('client_id'),
            client_secret=token_data.get('client_secret'),
            scopes=scopes_str,
            expiry=token_data.get('expiry'),
            google_email=token_data.get('google_email')
        )
        db.add(db_creds)
    
    await db.commit()
    await db.refresh(db_creds)
    return db_creds
async def get_user_by_id_async(db: AsyncSession, user_id: int) -> models.User | None:
    # db.get is the modern, async-native way to retrieve an object by its primary key.
    return await db.get(models.User, user_id)

def save_or_update_google_credentials(db: Session, user_id: int, creds_data: dict) -> models.GoogleCredentials:
    """Saves or updates Google credentials using specific columns for a single source of truth."""
    db_creds = get_google_credentials_by_user_id(db, user_id)
    print(creds_data)  # Debugging line to see the creds_data structure
    
    # Ensure scopes are a space-separated string
    scopes_str = ' '.join(creds_data.get('scopes', [])) if isinstance(creds_data.get('scopes'), list) else creds_data.get('scopes', '')

    if db_creds:
        # Update existing credentials
        print(f"DEBUG (CRUD-Sync): Updating creds for user {user_id}. Has new refresh_token: {creds_data.get('refresh_token') is not None}")
        db_creds.access_token = creds_data['access_token']
        print(f"access_token here in ===== save or update google: {db_creds.access_token}")
        # IMPORTANT: Only update refresh_token if a new one is provided.
        if new_refresh_token := creds_data.get('refresh_token'):
            db_creds.refresh_token = new_refresh_token
        db_creds.expiry = creds_data['expiry']
        db_creds.scopes = scopes_str
    else:
        # Create new credentials
        print(f"DEBUG (CRUD-Sync): Creating new creds for user {user_id}. Has refresh_token: {creds_data.get('refresh_token') is not None}")
        db_creds = models.GoogleCredentials(
            user_id=user_id,
            google_email=creds_data['google_email'],
            access_token=creds_data['access_token'],
            refresh_token=creds_data.get('refresh_token'),
            token_uri=creds_data['token_uri'],
            client_id=creds_data['client_id'],
            client_secret=creds_data['client_secret'],
            scopes=scopes_str,
            expiry=creds_data['expiry']
        )
        db.add(db_creds)
    
    db.commit()
    db.refresh(db_creds)
    return db_creds
async def save_or_update_google_credentials_async(db: AsyncSession, user_id: int, creds_data: dict) -> models.GoogleCredentials:
    """Asynchronously saves or updates Google credentials using specific columns."""
    result = await db.execute(select(models.GoogleCredentials).filter(models.GoogleCredentials.user_id == user_id))
    db_creds = result.scalars().first()
    
    scopes_str = ' '.join(creds_data.get('scopes', [])) if isinstance(creds_data.get('scopes'), list) else creds_data.get('scopes', '')

    if db_creds:
        print(f"DEBUG (CRUD-Async): Updating creds for user {user_id}. Has new refresh_token: {creds_data.get('refresh_token') is not None}")
        db_creds.access_token = creds_data['access_token']
        if new_refresh_token := creds_data.get('refresh_token'):
            db_creds.refresh_token = new_refresh_token
        db_creds.expiry = creds_data['expiry']
        db_creds.scopes = scopes_str
    else:
        print(f"DEBUG (CRUD-Async): Creating new creds for user {user_id}. Has refresh_token: {creds_data.get('refresh_token') is not None}")
        db_creds = models.GoogleCredentials(
            user_id=user_id,
            google_email=creds_data['google_email'],
            access_token=creds_data['access_token'],
            refresh_token=creds_data.get('refresh_token'),
            token_uri=creds_data['token_uri'],
            client_id=creds_data['client_id'],
            client_secret=creds_data['client_secret'],
            scopes=scopes_str,
            expiry=creds_data['expiry']
        )
        db.add(db_creds)
        
    await db.commit()
    await db.refresh(db_creds)
    return db_creds