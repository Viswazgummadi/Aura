from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import timedelta

from src.database import crud, database, models
from src.database.database import get_db
from src.core import security
from src.core import config
from src.core import gcp_auth # For Google auth flow logic

from src.database.models import UserCreate, UserResponse, Token, TokenData
from src.api.dependencies import get_current_user

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

# --- NEW: Google OAuth Endpoints (UPDATED) ---

@router.get("/google/login", status_code=status.HTTP_302_FOUND, response_class=RedirectResponse)
async def google_login(
    current_user: models.User = Depends(get_current_user), # User must be authenticated with AIBuddies first
    db: Session = Depends(get_db)
):
    """
    Initiates the Google OAuth 2.0 login flow for the authenticated AIBuddies user.
    Redirects the user to Google's authorization page.
    """
    print(f"API: Initiating Google OAuth for AIBuddies user ID: {current_user.id}")
    
    # 1. Create a unique, random state parameter for CSRF protection.
    # This state links the OAuth flow to the current AIBuddies user in our database.
    oauth_state_obj = crud.create_oauth_state(db, user_id=current_user.id)
    state_value_for_google = oauth_state_obj.state_value
    
    # 2. Generate the Google authorization URL, passing our generated state
    google_auth_url = gcp_auth.get_google_auth_url(state=state_value_for_google) # <-- Pass our state

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
        # gcp_auth.exchange_code_for_token will handle state verification and deletion
        await gcp_auth.exchange_code_for_token(auth_code=code, state=state) # <-- Pass the state to gcp_auth
        
        print(f"API: Google tokens successfully exchanged and saved.")
        return RedirectResponse(url="/docs?message=Google_Auth_Success", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        print(f"API ERROR: Google token exchange failed: {e}")
        # In a real app, you'd redirect to an error page, possibly with a message.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to exchange Google authorization code: {e}"
        )