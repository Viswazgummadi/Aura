#database/database.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# --- Configuration ---
load_dotenv()

# This is the path to our SQLite database file.
# It will be created in the root directory of our project as 'database.db'.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database.db")

# --- Engine Setup ---

# The 'engine' is the core interface to the database.
# It's how SQLAlchemy communicates with our 'database.db' file.
# The 'connect_args' is needed specifically for SQLite to allow it to be
# used in a multi-threaded environment like a web server.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL
)

# --- Session Setup ---

# A 'session' is the primary way we will interact with the database.
# Think of it as a temporary "conversation" with the database where you can
# add, update, or delete data.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Utility Functions ---

def get_db():
    """
    This function is a 'dependency' for our API endpoints.
    It creates a new database session for each incoming request and makes
    sure the session is closed when the request is finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_database_and_tables():
    """
    This function creates the database file and all the tables defined
    in our models.py file. We will call this once when our application starts.
    """
    print("--- Initializing database ---")
    
    # We need to import the Base from models.py so the engine knows about our tables.
    from .models import Base
    
    try:
        # This line reads the metadata from all classes that inherit from Base
        # and creates the corresponding tables in the database.
        Base.metadata.create_all(bind=engine)
        print("✅ Database and tables created successfully (if they didn't exist).")
    except Exception as e:
        print(f"❌ An error occurred while creating database tables: {e}")