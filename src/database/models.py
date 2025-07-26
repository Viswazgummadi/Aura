import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    ForeignKey,
    Boolean
)
from sqlalchemy.orm import declarative_base, relationship
from pydantic import BaseModel
from typing import List, Optional

Base = declarative_base()

# --- SQLAlchemy ORM Table Model Definitions ---

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    tasks = relationship("Task", back_populates="owner")
    notes = relationship("Note", back_populates="owner")
    google_credentials = relationship("GoogleCredentials", back_populates="user", uselist=False)
    # NEW RELATIONSHIP: A user can have multiple OAuth states (e.g., if they initiate multiple times)
    oauth_states = relationship("OAuthState", back_populates="user") 

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"

class GoogleCredentials(Base):
    __tablename__ = "google_credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    token = Column(Text, nullable=False)
    refresh_token = Column(String, nullable=True)
    token_uri = Column(String, nullable=True)
    client_id = Column(String, nullable=False)
    client_secret = Column(String, nullable=False)
    scopes = Column(Text, nullable=False)
    expiry = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="google_credentials")

    def __repr__(self):
        return f"<GoogleCredentials(user_id={self.user_id}, expiry={self.expiry})>"

# NEW MODEL: To securely store OAuth states for CSRF protection
class OAuthState(Base):
    __tablename__ = "oauth_states"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) # Link to the user who initiated the flow
    state_value = Column(String, unique=True, nullable=False, index=True) # The unique state string
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))

    user = relationship("User", back_populates="oauth_states") # Link back to the User

    def __repr__(self):
        return f"<OAuthState(id={self.id}, user_id={self.user_id}, state_value='{self.state_value[:10]}...')>"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    description = Column(String, nullable=False)
    status = Column(String, default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="tasks")

    def __repr__(self):
        return f"<Task(id='{self.id}', description='{self.description[:20]}...', status='{self.status}', user_id={self.user_id})>"

class Note(Base):
    __tablename__ = "notes"

    key = Column(String, primary_key=True, index=True)
    value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc), onupdate=datetime.datetime.now(datetime.timezone.utc))
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="notes")
    
    def __repr__(self):
        return f"<Note(key='{self.key}', value='{self.value[:20]}...', user_id={self.user_id})>"

# --- Pydantic Schemas (no changes here for now) ---

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None


class TaskBase(BaseModel):
    description: str

class TaskCreate(TaskBase):
    pass

class TaskResponse(TaskBase):
    id: str
    status: str
    created_at: datetime.datetime
    user_id: int

    class Config:
        from_attributes = True

class NoteBase(BaseModel):
    key: str
    value: str

class NoteCreate(NoteBase):
    pass

class NoteResponse(NoteBase):
    created_at: datetime.datetime
    updated_at: datetime.datetime
    user_id: int

    class Config:
        from_attributes = True