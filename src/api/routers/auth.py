from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import timedelta, datetime # <-- NEW IMPORT: datetime for expiry check
import json # <-- NEW IMPORT: for parsing JSON token data

from src.database import crud, database, models
from src.database.database import get_db
from src.core import security
from src.core import config
from src.core import gcp_auth # For Google auth flow logic

from src.database.models import UserCreate, UserResponse, Token, TokenData
from src.api.dependencies import get_current_user

# Import Credentials specifically for build_google_service if needed, but it's handled in gcp_auth.py
from google.oauth2.credentials import Credentials # <-- NEW IMPORT

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

# --- Endpoint for User Registration ---
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
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
    """
    Initiates the Google OAuth 2.0 login flow for the authenticated AIBuddies user.
    Redirects the user to Google's authorization page.
    """
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
    """
    Handles the callback from Google after user authorization.
    Exchanges the authorization code for access and refresh tokens, and saves them.
    """
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

# --- NEW: Google Credential Status Endpoint ---
@router.get("/google/status")
async def google_status(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Checks the status of the authenticated user's Google account connection.
    """
    print(f"API: Checking Google status for user ID: {current_user.id}")
    db_creds = crud.get_google_credentials_by_user_id(db, current_user.id)
    
    if not db_creds:
        return {"status": "not_connected", "detail": "Google account not linked."}
    
    # Reconstruct Credentials object to check validity
    try:
        creds_dict = json.loads(db_creds.token)
        creds_dict['token'] = creds_dict.get('access_token', creds_dict.get('token'))
        if isinstance(creds_dict.get('expiry'), str):
            creds_dict['expiry'] = datetime.fromisoformat(creds_dict['expiry'])
        
        # We need the full scopes list to properly validate credentials object.
        # It's safest to use the SCOPES defined in gcp_auth.py.
        creds = Credentials.from_authorized_user_info(creds_dict, gcp_auth.SCOPES)
        
        is_valid = creds.valid
        expiry_info = creds.expiry.isoformat() if creds.expiry else "N/A"
        
        return {
            "status": "connected",
            "detail": "Google account linked and credentials are valid (or refreshed).",
            "is_token_valid": is_valid,
            "expiry": expiry_info,
            "scopes": db_creds.scopes.split(',') if db_creds.scopes else [] # Ensure scopes is a list
        }
    except Exception as e:
        print(f"ERROR: Failed to verify Google credentials for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify linked Google credentials: {e}"
        )