from fastapi import FastAPI
from src.database.database import create_database_and_tables

# Import all your routers here
from .routers import tasks
from .routers import notes
from .routers import auth # <-- NEW IMPORT for auth router

# --- Main FastAPI Application Instance ---
app = FastAPI(
    title="AIBuddies API",
    description="The backend service for the AIBuddies personal assistant agent.",
    version="1.0.0",
)

# --- Startup Event Handler ---
@app.on_event("startup")
def on_startup():
    create_database_and_tables()

# --- Include Routers ---
app.include_router(tasks.router)
app.include_router(notes.router)
app.include_router(auth.router) # <-- NEW INCLUDE for auth router

# --- Root Endpoint ---
@app.get("/", tags=["Root"])
def read_root():
    """A welcome message for the API root."""
    return {"message": "Welcome to the AIBuddies API! Visit /docs for documentation."}