from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

from backend.storage.database import Database
from backend.storage.auth_records import UserRecord, SessionRecord
from backend.models.auth import UserRegister, UserLogin, UserResponse, TokenResponse
from backend.services.auth_service import get_password_hash, verify_password, create_access_token, create_refresh_token, REFRESH_TOKEN_EXPIRE_DAYS
from backend.api.dependencies import get_session

router = APIRouter(prefix="/auth", tags=["auth"])

def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    # Set HTTP-only secure cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True, # Should be true in production, False in dev if no HTTPS
        samesite="lax",
        max_age=30 * 60 # 30 minutes
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_session)):
    query = select(UserRecord).where(UserRecord.email == user_data.email)
    result = await db.execute(query)
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = UserRecord(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password)
    )
    db.add(new_user)
    try:
        await db.commit()
        await db.refresh(new_user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Database error during registration")

    return UserResponse(id=new_user.id, email=new_user.email, is_active=new_user.is_active)

@router.post("/login")
async def login(response: Response, user_data: UserLogin, request: Request, db: AsyncSession = Depends(get_session)):
    query = select(UserRecord).where(UserRecord.email == user_data.email)
    result = await db.execute(query)
    user = result.scalars().first()

    if not user or not user.hashed_password or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token()

    # Store session in DB
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    db_session = SessionRecord(
        user_id=user.id,
        session_token=refresh_token,
        expires_at=expires_at,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(db_session)
    await db.commit()

    set_auth_cookies(response, access_token, refresh_token)
    return {"message": "Login successful", "user": {"id": user.id, "email": user.email}}

@router.post("/refresh")
async def refresh_token(request: Request, response: Response, db: AsyncSession = Depends(get_session)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    query = select(SessionRecord).where(
        SessionRecord.session_token == refresh_token,
        SessionRecord.is_active == True,
        SessionRecord.expires_at > datetime.now(timezone.utc)
    )
    result = await db.execute(query)
    session = result.scalars().first()

    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    # Rotate refresh token
    new_refresh_token = create_refresh_token()
    session.session_token = new_refresh_token
    session.expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token = create_access_token(session.user_id)
    await db.commit()

    set_auth_cookies(response, access_token, new_refresh_token)
    return {"message": "Token refreshed successfully"}

@router.post("/logout")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_session)):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        query = select(SessionRecord).where(SessionRecord.session_token == refresh_token)
        result = await db.execute(query)
        session = result.scalars().first()
        if session:
            session.is_active = False
            await db.commit()

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}
