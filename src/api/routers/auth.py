# src/api/routers/auth.py

# FastAPI Core Imports
from fastapi import (
    APIRouter, Depends, HTTPException, status, Query, WebSocket,
    BackgroundTasks
)
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse

# Python Standard Library
import json
from datetime import timedelta, datetime, timezone 

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
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ... (this function is correct, no changes needed)
    print(f"API: Initiating Google OAuth for AIBuddies user ID: {current_user.id}")
    oauth_state_obj = crud.create_oauth_state(db, user_id=current_user.id)
    state_value_for_google = oauth_state_obj.state_value
    
    google_auth_url = gcp_auth.get_google_auth_url(state=state_value_for_google)

    print(f"API: Redirecting user {current_user.id} to Google for authorization.")
    return RedirectResponse(google_auth_url)


@router.get("/google/callback")
async def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    scope: str = Query(..., description="Scopes granted by the user (space-separated)"),
    db: Session = Depends(get_db)
):
    # ... (this function is correct, no changes needed)
    print(f"API: Google OAuth callback received. State: {state}, Code: {code}")

    try:
        await gcp_auth.exchange_code_for_token(auth_code=code, state=state)
        
        print(f"API: Google tokens successfully exchanged and saved.")
        return RedirectResponse(url="/docs?message=Google_Auth_Success", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        print(f"API ERROR: Google token exchange failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to exchange Google authorization code: {e}"
        )


# --- Google Credential Status Endpoint ---
@router.get("/google/status")
async def google_status(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ... (this function is correct, no changes needed)
    print(f"API: Checking Google status for user ID: {current_user.id}")
    db_creds = crud.get_google_credentials_by_user_id(db, current_user.id)
    
    if not db_creds:
        return {"status": "not_connected", "detail": "Google account not linked."}
    
    try:
        token_data_from_db = json.loads(db_creds.token)
        expiry_str = token_data_from_db.get('expiry')
        is_token_valid = False
        expiry_info = "N/A"
        now_utc = datetime.now(timezone.utc)

        if expiry_str:
            if expiry_str.endswith("Z"):
                expiry_str = expiry_str.replace("Z", "+00:00")
            
            try:
                creds_expiry_dt = datetime.fromisoformat(expiry_str)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Invalid expiry datetime format: {expiry_str}"
                )
            
            is_token_valid = creds_expiry_dt > now_utc
            expiry_info = creds_expiry_dt.isoformat()
        
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