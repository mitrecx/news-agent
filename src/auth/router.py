"""Authentication router for login and registration"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .models import UserCreate, UserLogin, Token, User
from .database import get_db
from .user_service import UserService
from .security import create_access_token, decode_access_token
import asyncpg

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


@router.post("/register", response_model=Token)
async def register(user_data: UserCreate, conn: asyncpg.Connection = Depends(get_db)):
    """
    Register a new user

    Returns an access token upon successful registration
    """
    # Check if user already exists
    existing_user = await UserService.get_user_by_username(conn, user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Create user
    user = await UserService.create_user(conn, user_data)

    # Create access token
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id}
    )

    return Token(
        access_token=access_token,
        user=User(id=user.id, username=user.username, email=user.email)
    )


@router.post("/login", response_model=Token)
async def login(login_data: UserLogin, conn: asyncpg.Connection = Depends(get_db)):
    """
    Login with username and password

    Returns an access token upon successful authentication
    """
    user = await UserService.authenticate_user(conn, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id}
    )

    return Token(
        access_token=access_token,
        user=User(id=user.id, username=user.username, email=user.email)
    )


@router.get("/me", response_model=User)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get the current authenticated user
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("sub")
    user_id = payload.get("user_id")

    if username is None or user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await UserService.get_user_by_id(conn, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    conn: asyncpg.Connection = Depends(get_db)
) -> User | None:
    """
    Get the current authenticated user, or None if not authenticated
    """
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials, conn)
    except HTTPException:
        return None
