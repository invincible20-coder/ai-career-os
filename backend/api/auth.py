from datetime import datetime, timedelta, timezone
import os
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

from backend.storage.auth_records import (
    IdentityIntelligenceRecord,
    LinkedAccountRecord,
    SessionRecord,
    UserRecord,
    utc_now,
)
from backend.models.auth import (
    IdentityGraph,
    OAuthLinkRequest,
    OAuthProvider,
    UserRegister,
    UserLogin,
    UserResponse,
)
from backend.services.auth_service import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token,
    get_password_hash,
    infer_provider_intelligence,
    oauth_provider_configs,
    protect_refresh_token,
    verify_password,
)
from backend.api.dependencies import get_session
from backend.core.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])

def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    settings = get_settings()
    cookie_secure = settings.auth_cookie_secure and not settings.debug
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=cookie_secure,
        samesite="lax",
        max_age=30 * 60 # 30 minutes
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=cookie_secure,
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


@router.get("/oauth/providers")
async def oauth_providers(request: Request):
    settings = request.app.state.settings
    return {
        "providers": [
            config.model_dump(mode="json")
            for config in oauth_provider_configs(
                enabled_providers=settings.oauth_enabled_providers,
                redirect_base_url=settings.oauth_redirect_base_url,
            )
        ]
    }


@router.get("/oauth/{provider}/authorize")
async def oauth_authorize(provider: OAuthProvider, request: Request):
    settings = request.app.state.settings
    configs = {
        config.provider: config
        for config in oauth_provider_configs(
            enabled_providers=settings.oauth_enabled_providers,
            redirect_base_url=settings.oauth_redirect_base_url,
        )
    }
    config = configs[provider]
    if not config.enabled or not config.authorization_url:
        raise HTTPException(
            status_code=400,
            detail=f"OAuth provider '{provider.value}' is not configured",
        )
    client_id = os.getenv(f"{provider.value.upper()}_CLIENT_ID", "")
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": config.callback_url,
            "response_type": "code",
            "scope": " ".join(config.scopes),
            "state": create_refresh_token(),
        }
    )
    return {"provider": provider.value, "authorization_url": f"{config.authorization_url}?{query}"}


@router.get("/oauth/{provider}/callback")
async def oauth_callback(provider: OAuthProvider, code: str | None = None, state: str | None = None):
    if not code:
        raise HTTPException(status_code=400, detail="OAuth callback missing code")
    return {
        "provider": provider.value,
        "state": state,
        "message": "Authorization code received. Configure provider client secret to exchange and link this account.",
    }


@router.post("/oauth/link-local/{user_id}")
async def link_local_provider(
    user_id: str,
    payload: OAuthLinkRequest,
    db: AsyncSession = Depends(get_session),
):
    user = await db.get(UserRecord, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    intelligence = infer_provider_intelligence(
        provider=payload.provider,
        metadata=payload.metadata,
    )
    existing_account = await db.scalar(
        select(LinkedAccountRecord)
        .where(LinkedAccountRecord.provider == payload.provider.value)
        .where(LinkedAccountRecord.provider_account_id == payload.provider_account_id)
    )
    if existing_account is not None and existing_account.user_id != user_id:
        raise HTTPException(
            status_code=409,
            detail="Provider account is already linked to another user",
        )
    if existing_account is not None:
        existing_account.encrypted_refresh_token = protect_refresh_token(
            payload.metadata.get("refresh_token")
        )
        existing_account.metadata_json = payload.metadata
    else:
        db.add(
            LinkedAccountRecord(
                user_id=user_id,
                provider=payload.provider.value,
                provider_account_id=payload.provider_account_id,
                encrypted_refresh_token=protect_refresh_token(payload.metadata.get("refresh_token")),
                access_token=None,
                metadata_json=payload.metadata,
                created_at=utc_now(),
            )
        )
    existing = await db.get(IdentityIntelligenceRecord, user_id)
    provider_payload = (
        dict(existing.provider_intelligence_json)
        if existing is not None
        else {}
    )
    provider_payload[payload.provider.value] = intelligence.model_dump(mode="json")
    await db.merge(
        IdentityIntelligenceRecord(
            user_id=user_id,
            provider_intelligence_json=provider_payload,
            adaptive_memory_json={
                "behavioral_memory_key": f"user:{user_id}:behavior",
                "recommendation_history_key": f"user:{user_id}:recommendations",
                "resume_memory_key": f"user:{user_id}:resumes",
                "outcome_memory_key": f"user:{user_id}:outcomes",
            },
            updated_at=utc_now(),
        )
    )
    await db.commit()
    return {"linked": True, "provider_intelligence": intelligence.model_dump(mode="json")}


@router.get("/identity-graph/{user_id}")
async def identity_graph(user_id: str, db: AsyncSession = Depends(get_session)):
    user = await db.get(UserRecord, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    accounts = list(
        (
            await db.scalars(
                select(LinkedAccountRecord).where(LinkedAccountRecord.user_id == user_id)
            )
        ).all()
    )
    intelligence = await db.get(IdentityIntelligenceRecord, user_id)
    now = utc_now()
    graph = IdentityGraph(
        user_id=user_id,
        email=user.email,
        linked_providers=[OAuthProvider(account.provider) for account in accounts],
        behavioral_memory_key=f"user:{user_id}:behavior",
        recommendation_history_key=f"user:{user_id}:recommendations",
        resume_memory_key=f"user:{user_id}:resumes",
        outcome_memory_key=f"user:{user_id}:outcomes",
        provider_intelligence=(
            intelligence.provider_intelligence_json if intelligence is not None else {}
        ),
        updated_at=intelligence.updated_at if intelligence is not None else now,
    )
    return graph.model_dump(mode="json")
