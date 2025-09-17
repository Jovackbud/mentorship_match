# src/routers/auth_router.py
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime, timezone

from ..database import get_db
from ..schemas import UserCreate, UserResponse, Token
from ..models import User, Mentor, Mentee
from ..security import authenticate_user, create_access_token, get_password_hash, get_current_user
from ..config import get_settings
from ..constants import ErrorMessages

router = APIRouter(tags=["authentication"])
settings = get_settings()

@router.post("/register", response_model=UserResponse, status_code=201)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=409, detail="Username already registered")
    
    db_user = User(
        username=user.username,
        hashed_password=get_password_hash(user.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/token", response_model=Token)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login and set HttpOnly cookie, also return OAuth2 token payload"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire_time_utc = datetime.now(timezone.utc) + access_token_expires
    
    access_token = create_access_token(
        data={"sub": user.username}, 
        expires_delta=access_token_expires
    )
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=expire_time_utc,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user profile with associated mentor/mentee IDs"""
    mentor_profile = db.query(Mentor).filter(Mentor.user_id == current_user.id).first()
    mentee_profile = db.query(Mentee).filter(Mentee.user_id == current_user.id).first()

    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        mentor_profile_id=mentor_profile.id if mentor_profile else None,
        mentee_profile_id=mentee_profile.id if mentee_profile else None,
    )

@router.post("/logout", status_code=200)
async def logout(response: Response):
    """Logout user by clearing cookie"""
    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully"}