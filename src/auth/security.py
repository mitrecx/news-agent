"""Security utilities for password hashing and JWT tokens.

This module provides secure password hashing using bcrypt and JWT token
management for authentication.
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
import secrets
import logging
from ..agent.config import get_settings

logger = logging.getLogger(__name__)

# JWT settings - loaded from config
settings = get_settings()
SECRET_KEY: str = settings.jwt_secret
ALGORITHM: str = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES: int = settings.jwt_access_token_expire_minutes


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a bcrypt hash.

    Args:
        plain_password: The plain text password to verify
        hashed_password: The bcrypt hashed password

    Returns:
        True if password matches, False otherwise
    """
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt with salt.

    Args:
        password: The plain text password to hash

    Returns:
        The bcrypt hashed password as a string

    Raises:
        ValueError: If password is empty or too short
    """
    if not password:
        raise ValueError("Password cannot be empty")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters")

    salt = bcrypt.gensalt(rounds=12)  # Use 12 rounds for better security
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token with expiration.

    Args:
        data: The payload data to encode (e.g., {"sub": username, "user_id": id})
        expires_delta: Optional custom expiration time

    Returns:
        The encoded JWT token

    Raises:
        ValueError: If SECRET_KEY is not configured
    """
    if not SECRET_KEY or SECRET_KEY == "your-secret-key-change-this-in-production":
        raise ValueError(
            "JWT_SECRET not configured. "
            "Set a strong secret key in environment variables."
        )

    to_encode = data.copy()

    # Set expiration
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Add issued-at and expiration claims
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow()
    })

    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.debug(f"Created JWT token for user: {data.get('sub', 'unknown')}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Failed to create JWT token: {e}")
        raise


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT token.

    Args:
        token: The JWT token to decode

    Returns:
        The decoded payload if valid, None otherwise
    """
    if not token:
        logger.warning("Empty token provided")
        return None

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={
                "verify_exp": True,
                "verify_iat": True
            }
        )
        logger.debug(f"Successfully decoded JWT token for user: {payload.get('sub', 'unknown')}")
        return payload
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error decoding token: {e}")
        return None
