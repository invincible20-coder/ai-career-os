from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class OAuthProvider(str, Enum):
    GOOGLE = "google"
    GITHUB = "github"
    LINKEDIN = "linkedin"
    APPLE = "apple"
    MICROSOFT = "microsoft"
    DISCORD = "discord"

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    
class UserResponse(BaseModel):
    id: str
    email: EmailStr
    is_active: bool


class OAuthProviderConfig(BaseModel):
    provider: OAuthProvider
    enabled: bool
    authorization_url: str | None = None
    callback_url: str
    scopes: list[str] = Field(default_factory=list)


class OAuthLinkRequest(BaseModel):
    provider: OAuthProvider
    provider_account_id: str = Field(..., min_length=1, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderIntelligence(BaseModel):
    provider: OAuthProvider
    signals: dict[str, float] = Field(default_factory=dict)
    summary: str = ""
    evidence: list[str] = Field(default_factory=list)
    updated_at: datetime


class IdentityGraph(BaseModel):
    user_id: str
    email: EmailStr
    linked_providers: list[OAuthProvider] = Field(default_factory=list)
    behavioral_memory_key: str
    recommendation_history_key: str
    resume_memory_key: str
    outcome_memory_key: str
    provider_intelligence: dict[str, ProviderIntelligence] = Field(default_factory=dict)
    updated_at: datetime
