# src/api/server.py
from fastapi import FastAPI
from src.database.database import create_database_and_tables
from .routers import admin
from .routers import tasks
from .routers import notes
from .routers import auth
from .routers import calendar # <-- NEW IMPORT
from .routers import gmail    # <-- NEW IMPORT
from .routers import notifications
from .routers import agent
from fastapi.middleware.cors import CORSMiddleware
# --- Main FastAPI Application Instance ---
app = FastAPI(
    title="AIBuddies API",
    description="The backend service for the AIBuddies personal assistant agent.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for testing. Use specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- Startup Event Handler ---
@app.on_event("startup")
async def on_startup(): # <-- Make async
    await create_database_and_tables() 

# --- Include Routers ---
app.include_router(tasks.router)
app.include_router(notes.router)
app.include_router(auth.router)
app.include_router(calendar.router) # <-- NEW INCLUDE
app.include_router(gmail.router)    # <-- NEW INCLUDE
app.include_router(notifications.router)
app.include_router(notes.router_tags)
app.include_router(admin.router)
app.include_router(agent.router)
# --- Root Endpoint ---
@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the AIBuddies API! Visit /docs for documentation."}