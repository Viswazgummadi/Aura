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


# --- Note CRUD Functions (existing, no changes) ---
def get_note_by_key(db: Session, key: str, user_id: int) -> models.Note | None:
    return db.query(models.Note).filter(models.Note.key == key.lower().strip(), models.Note.user_id == user_id).first()

def get_all_notes(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> list[models.Note]:
    return db.query(models.Note).filter(models.Note.user_id == user_id).offset(skip).limit(limit).all()

def create_or_update_note(db: Session, key: str, value: str, user_id: int) -> models.Note:
    normalized_key = key.lower().strip()
    db_note = get_note_by_key(db, normalized_key, user_id)
    
    if db_note:
        db_note.value = value
        db_note.updated_at = datetime.datetime.now(datetime.timezone.utc)
    else:
        db_note = models.Note(key=normalized_key, value=value, user_id=user_id)
        db.add(db_note)
        
    db.commit()
    db.refresh(db_note)
    return db_note

def delete_note_by_key(db: Session, key: str, user_id: int) -> bool:
    normalized_key = key.lower().strip()
    db_note = get_note_by_key(db, normalized_key, user_id)
    
    if db_note:
        db.delete(db_note)
        db.commit()
        return True
    return False