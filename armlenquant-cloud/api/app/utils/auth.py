"""
Authentication Utilities
"""
from datetime import datetime, timedelta
from typing import Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Header
from fastapi.security import HTTPBearer
from app.config import get_settings
from app.models.user import User

settings = get_settings()

# Password hashing - use pbkdf2_sha256 which is pure Python and works on all platforms
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# JWT Bearer scheme
security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str, email: str, is_admin: bool = False) -> Tuple[str, datetime]:
    """
    Create a JWT access token.
    
    Returns:
        tuple: (token, expiry_datetime)
    """
    expires = datetime.utcnow() + timedelta(hours=settings.jwt_expiry_hours)
    
    payload = {
        "sub": user_id,
        "email": email,
        "is_admin": is_admin,
        "exp": expires,
        "iat": datetime.utcnow(),
        "type": "access"
    }
    
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token, 
            settings.jwt_secret, 
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(credentials=Depends(security)) -> User:
    """
    Dependency to get current authenticated user from JWT.
    """
    token = credentials.credentials
    payload = decode_token(token)

    return User(
        user_id=payload["sub"],
        email=payload["email"],
        is_admin=payload.get("is_admin", False)
    )


async def verify_agent_secret(x_agent_secret: str = Header(...)) -> bool:
    """
    Dependency to verify agent API key.
    Used for local poller authentication.
    """
    if x_agent_secret != settings.agent_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent secret"
        )
    return True

