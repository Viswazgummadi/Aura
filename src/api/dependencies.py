from fastapi import Depends, HTTPException, status,Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from src.database import crud, models
from src.database.database import get_db
from src.core import security

# Instantiate the OAuth2PasswordBearer for dependency injection
# The tokenUrl points to our login endpoint where clients can get a token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

async def get_current_user(
    token: str = Depends(oauth2_scheme), # FastAPI will inject the token from the header
    db: Session = Depends(get_db)
) -> models.User:
    """
    Dependency that retrieves and authenticates the current user based on the JWT token.
    
    Args:
        token (str): The JWT token extracted from the Authorization header by OAuth2PasswordBearer.
        db (Session): The database session.
        
    Returns:
        models.User: The authenticated User object.
        
    Raises:
        HTTPException 401: If the token is invalid, expired, or the user is not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Decode the token to get the payload (user_id and email)
    payload = security.decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id: int = payload.get("user_id")
    if user_id is None:
        raise credentials_exception
    
    # Retrieve the user from the database
    user = crud.get_user_by_id(db, user_id=user_id)
    if user is None:
        raise credentials_exception
    
    # You might want to add a check for user.is_active here as well.
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user

async def get_current_user_from_ws(
    token: str = Query(...), # The token will be passed as a query parameter
    db: Session = Depends(get_db)
) -> models.User:
    """
    Dependency for authenticating users via WebSockets.
    The token is expected as a query parameter, e.g., "ws://.../?token=...".
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = security.decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id: int = payload.get("user_id")
    if user_id is None:
        raise credentials_exception
    
    user = crud.get_user_by_id(db, user_id=user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    
    return user
