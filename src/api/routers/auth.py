# src/api/routers/auth.py

# FastAPI Core Imports
from fastapi import (
    APIRouter, Depends, HTTPException, status, Query, WebSocket,
    BackgroundTasks,Request
)
from dateutil.parser import isoparse
from src.api.dependencies import get_current_user, get_current_user_from_ws, get_current_user_async

from src.database.database import get_db, get_async_db
from sqlalchemy.ext.asyncio import AsyncSession


from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse

# Python Standard Library
import json
from datetime import timedelta, datetime, timezone 
import asyncio

# SQLAlchemy
from sqlalchemy.orm import Session

# Project-specific Imports
from src.core import config, gcp_auth, security
from src.database import crud, database, models
from src.database.database import get_db
from src.api.dependencies import get_current_user, get_current_user_from_ws
from src.api.connection_manager import manager

# Pydantic Models
from src.database.models import UserCreate, UserResponse, Token, TokenData

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

# --- Endpoint for User Registration ---
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # ... (this function is correct, no changes needed)
    print(f"API: Received registration request for email: {user.email}")
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    new_user = crud.create_user(db=db, email=user.email, password=user.password)
    print(f"API: User registered successfully: {new_user.email}")
    return new_user

# --- Endpoint for User Login and Token Generation ---
@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # ... (this function is correct, no changes needed)
    user = crud.get_user_by_email(db, email=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    print(f"API: User logged in, token issued for: {user.email}")
    return {"access_token": access_token, "token_type": "bearer"}


# --- Google OAuth Endpoints ---
@router.get("/google/login", status_code=status.HTTP_302_FOUND, response_class=RedirectResponse)
async def google_login(
    request:Request,
    current_user: models.User = Depends(get_current_user_async), # <-- USE THE ASYNC DEPENDENCY
    db: AsyncSession = Depends(get_async_db)
):
   
    oauth_state_obj = await crud.create_oauth_state_async(db, user_id=current_user.id)
    state_value_for_google = oauth_state_obj.state_value
    print(f"DEBUG: Created OAuth state in DB: '{state_value_for_google}'")

    google_auth_url = gcp_auth.get_google_auth_url(state=state_value_for_google)
    print("google_auth_url:",google_auth_url)
    print(f"API: Redirecting user {current_user.id} to Google for authorization.")
    return RedirectResponse(google_auth_url)



@router.get("/google/callback")
async def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    # 'scope' is no longer needed here as the flow object handles it
    db: AsyncSession = Depends(get_async_db) 
):
    try:
        print(f"API: Received Google callback with state: {state}")
        # The refactored function is much cleaner to call
        
        await gcp_auth.exchange_code_for_token(auth_code=code, state=state, db=db)
        
        # Redirecting to a success page (your frontend can handle this)
        return RedirectResponse(url="/docs?message=Google_Auth_Success", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        # Log the full error server-side for debugging
        print(f"API ERROR: Complete failure in Google callback flow. Error: {e}")
        # Provide a user-friendly error message
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, # Use 400 for a bad request from user/google
            detail=f"Authentication failed. Could not process Google authorization. Please try again. Server error: {str(e)}"
        )
# --- Google Credential Status Endpoint ---
@router.get("/google/status")
async def google_status(
    current_user: models.User = Depends(get_current_user_async), 
    db: Session = Depends(get_db)
):
    # ... (this function is correct, no changes needed)
    print(f"API: Checking Google status for user ID: {current_user.id}")
    db_creds = crud.get_google_credentials_by_user_id(db, current_user.id)
    print("db_creds: ", db_creds.token)
    
    if not db_creds:
        return {"status": "not_connected", "detail": "Google account not linked."}
    
    try:
        token_data_from_db = db_creds.access_token
        print("token_data_from_db:", token_data_from_db)
        
        is_token_valid = False
        expiry_info = "N/A"
        now_utc = datetime.now(timezone.utc)

        if isinstance(db_creds.expiry, datetime):
            creds_expiry_dt = db_creds.expiry
        # Make sure both are timezone-aware for comparison
            if creds_expiry_dt.tzinfo is None:
                creds_expiry_dt = creds_expiry_dt.replace(tzinfo=timezone.utc)
            print("current time:",now_utc,type(now_utc))
            print("expiry time:",creds_expiry_dt,type(creds_expiry_dt))
            # Check if the token is still valid
            is_token_valid = creds_expiry_dt > now_utc
            expiry_info = creds_expiry_dt.isoformat()
        else:
            raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Invalid expiry type: {type(db_creds.expiry)}"
    )

        return {
            "status": "connected",
            "detail": "Google account linked and credentials are valid.",
            "is_token_valid": is_token_valid,
            "expiry": expiry_info,
            "scopes": db_creds.scopes.split(',') if db_creds.scopes else []
        }
    except Exception as e:
        print(f"ERROR: Failed to verify Google credentials for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify linked Google credentials: {e}"
        )


# --- NEW: WebSocket Endpoint for Real-Time Notifications ---
@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, # <- The fix is that WebSocket is now correctly imported
    current_user: models.User = Depends(get_current_user_from_ws)
):
    """
    Handles the persistent WebSocket connection for a logged-in user.
    The client must connect to "wss://<your-domain>/auth/ws?token=<jwt_token>".
    """
    await manager.connect(current_user.id, websocket)
    print(f"INFO: WebSocket connection established for user {current_user.id}")
    try:
        # This loop keeps the connection alive.
        while True:
            await websocket.receive_text()
    except Exception:
        # This block will execute when the client disconnects.
        pass
    finally:
        manager.disconnect(current_user.id)
        print(f"INFO: WebSocket connection closed for user {current_user.id}")