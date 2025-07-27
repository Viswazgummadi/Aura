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
from sqlalchemy import Table
Base = declarative_base()
note_tag_association_table = Table(
    "note_tag_association",
    Base.metadata,
    Column("note_id", Integer, ForeignKey("notes.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)
class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True, nullable=False)

    # This relationship is defined by the association table
    notes = relationship(
        "Note", secondary=note_tag_association_table, back_populates="tags"
    )

    def __repr__(self):
        return f"<Tag(id={self.id}, name='{self.name}')>"
# --- SQLAlchemy ORM Table Model Definitions (existing, no changes) ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    tasks = relationship("Task", back_populates="owner")
    notes = relationship("Note", back_populates="owner")
    google_credentials = relationship("GoogleCredentials", back_populates="user", uselist=False)
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

class OAuthState(Base):
    __tablename__ = "oauth_states"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    state_value = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    user = relationship("User", back_populates="oauth_states")

    def __repr__(self):
        return f"<OAuthState(id={self.id}, user_id={self.user_id}, state_value='{self.state_value[:10]}...')>"

class Task(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True, index=True)
    description = Column(String, nullable=False)
    status = Column(String, default="pending", nullable=False)

    priority = Column(String, default="medium", nullable=False) # e.g., "low", "medium", "high"
    due_date = Column(DateTime, nullable=True, index=True) # Optional due date, indexed for faster sorting


    created_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="tasks")

    def __repr__(self):
        return f"<Task(id='{self.id}', description='{self.description[:20]}...', status='{self.status}', user_id={self.user_id})>"

class Note(Base):
    __tablename__ = "notes"
    
    # The new structure with a proper ID, title, and content
    id = Column(Integer, primary_key=True, autoincrement=True) 
    title = Column(String, index=True, nullable=False)
    content = Column(Text, nullable=True) # Content can be optional
    
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc), onupdate=datetime.datetime.now(datetime.timezone.utc))
    
    # The note still belongs to a user
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tags = relationship(
        "Tag", secondary=note_tag_association_table, back_populates="notes"
    )

    owner = relationship("User", back_populates="notes")
    def __repr__(self):
        return f"<Note(id={self.id}, title='{self.title[:20]}...', user_id={self.user_id})>"

# --- Pydantic Schemas (existing) ---
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
    # Make priority and due_date optional during creation, with sensible defaults
    priority: Optional[str] = "medium"
    # The frontend should send due_date as an ISO 8601 string (e.g., "2025-12-31T23:59:59Z")
    due_date: Optional[datetime.datetime] = None
class TaskUpdate(BaseModel):
    # For updates, all fields are optional
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime.datetime] = None
class TaskResponse(TaskBase):
    id: str
    status: str
    priority: str
    due_date: Optional[datetime.datetime]
    created_at: datetime.datetime
    user_id: int

    class Config:
        from_attributes = True
        
# --- NEW: Pydantic Schemas for Tag ---
class TagBase(BaseModel):
    name: str

class TagCreate(TagBase):
    pass

class TagResponse(TagBase):
    id: int

    class Config:
        from_attributes = True

# ADD THESE NEW CLASSES IN THEIR PLACE
class NoteBase(BaseModel):
    title: str
    content: Optional[str] = None

class NoteCreate(NoteBase):
    pass

class NoteUpdate(BaseModel):
    # For updates, all fields can be optional
    title: Optional[str] = None
    content: Optional[str] = None

class NoteResponse(NoteBase):
    id: int
    tags: List[TagResponse] = []
    created_at: datetime.datetime
    updated_at: datetime.datetime
    user_id: int

    class Config:
        from_attributes = True

# --- NEW PYDANTIC SCHEMAS FOR CALENDAR AND GMAIL ---

# Calendar Schemas
class CalendarEventUpdate(BaseModel):
    # All fields are optional for updates
    summary: Optional[str] = None
    start_time_iso: Optional[str] = None
    end_time_iso: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
class CalendarEventBase(BaseModel):
    summary: str
    # Use str for ISO formatted dates for input
    start_time_iso: str # e.g., "YYYY-MM-DDTHH:MM:SSZ"
    end_time_iso: str
    description: Optional[str] = None
    location: Optional[str] = None

class CalendarEventCreate(CalendarEventBase):
    pass

class CalendarEventResponse(CalendarEventBase):
    id: str # Google Calendar event ID
    html_link: Optional[str] = None # Link to the event on Google Calendar

    class Config:
        extra = 'allow' # Allow extra fields from Google API response, if not explicitly defined here

# Gmail Schemas
class GmailMessageResponse(BaseModel):
    id: str
    threadId: Optional[str] = None
    subject: str
    sender: str
    historyId: Optional[int] = None
    delivered_to: Optional[str] = None

    class Config:
        extra = 'allow' # Allow extra fields from Google API response
class GmailSendRequest(BaseModel):
    to: str
    subject: str
    body: str
