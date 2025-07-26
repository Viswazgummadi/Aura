from fastapi import FastAPI
from src.database.database import create_database_and_tables

from .routers import tasks
from .routers import notes
from .routers import auth
from .routers import calendar # <-- NEW IMPORT
from .routers import gmail    # <-- NEW IMPORT

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
app.include_router(auth.router)
app.include_router(calendar.router) # <-- NEW INCLUDE
app.include_router(gmail.router)    # <-- NEW INCLUDE

# --- Root Endpoint ---
@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the AIBuddies API! Visit /docs for documentation."}