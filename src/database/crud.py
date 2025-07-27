import uuid
import datetime
import json
from typing import List, Optional

from sqlalchemy.orm import Session
import secrets
from . import models
from src.core.security import get_password_hash
from src.core.config import DateTimeEncoder # <-- NEW IMPORT: Our custom JSON encoder

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
            expiry=token_data.get('expiry')
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

# --- Task CRUD Functions (existing, no changes) ---
def get_task_by_id(db: Session, task_id: str, user_id: int) -> models.Task | None:
    return db.query(models.Task).filter(models.Task.id == task_id, models.Task.user_id == user_id).first()

def get_tasks_by_status(db: Session, status: str, user_id: int, skip: int = 0, limit: int = 100) -> list[models.Task]:
    return db.query(models.Task).filter(models.Task.status == status, models.Task.user_id == user_id).offset(skip).limit(limit).all()

def get_all_tasks(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> list[models.Task]:
    return db.query(models.Task).filter(models.Task.user_id == user_id).offset(skip).limit(limit).all()

def create_task(db: Session, description: str, user_id: int) -> models.Task:
    new_task_id = str(uuid.uuid4())[:8]
    db_task = models.Task(id=new_task_id, description=description, user_id=user_id)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def update_task_status(db: Session, task_id: str, user_id: int, new_status: str) -> models.Task | None:
    db_task = get_task_by_id(db, task_id, user_id)
    if db_task:
        db_task.status = new_status
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