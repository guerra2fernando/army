"""
Authentication Routes
"""
from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, HTTPException, status, Depends
from loguru import logger

from app.db import Database
from app.models.user import UserCreate, UserLogin, UserResponse, TokenResponse, User
from app.models.base import APIResponse
from app.utils.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=APIResponse)
async def register(user_data: UserCreate):
    """Register a new user."""
    
    users = Database.get_collection("users")
    
    # Check if email exists
    existing = await users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user_doc = {
        "_id": str(uuid4()),
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "name": user_data.name,
        "is_active": True,
        "is_admin": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    await users.insert_one(user_doc)
    
    logger.info(f"User registered: {user_data.email}")
    
    return APIResponse(
        success=True,
        message="User registered successfully",
        data={"user_id": user_doc["_id"]}
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Login and get access token."""
    
    users = Database.get_collection("users")
    
    # Find user
    user = await users.find_one({"email": credentials.email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if active
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    # Update last login
    await users.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    # Create token
    token, expires = create_access_token(
        user_id=user["_id"],
        email=user["email"],
        is_admin=user.get("is_admin", False)
    )
    
    logger.info(f"User logged in: {user['email']}")
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=int((expires - datetime.utcnow()).total_seconds()),
        user=UserResponse(
            id=user["_id"],
            email=user["email"],
            name=user["name"],
            is_active=user["is_active"],
            is_admin=user.get("is_admin", False),
            created_at=user["created_at"]
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile."""

    users = Database.get_collection("users")
    user = await users.find_one({"_id": current_user.user_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user["_id"],
        email=user["email"],
        name=user["name"],
        is_active=user["is_active"],
        is_admin=user.get("is_admin", False),
        created_at=user["created_at"]
    )

