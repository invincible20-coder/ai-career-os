from datetime import datetime, timedelta, timezone
import hashlib
import hmac
from passlib.hash import argon2
from joserfc import jwt
from joserfc.jwk import OctKey
import os
import uuid

from backend.models.auth import OAuthProvider, OAuthProviderConfig, ProviderIntelligence

# In a real system, these would be loaded from Settings/Env
_JWT_SECRET_RAW = os.environ.get("JWT_SECRET_KEY", "dev-secret-key-do-not-use-in-prod-huntai")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Build the key once at module load time
_JWT_KEY = OctKey.import_key(_JWT_SECRET_RAW.encode())


def get_password_hash(password: str) -> str:
    return argon2.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return argon2.verify(plain_password, hashed_password)


def create_access_token(subject: str) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": subject,
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode({"alg": JWT_ALGORITHM}, claims, _JWT_KEY)


def create_refresh_token() -> str:
    return str(uuid.uuid4())


def verify_access_token(token: str) -> dict | None:
    """Decode and validate a JWT access token. Returns the claims dict or None."""
    try:
        token_obj = jwt.decode(token, _JWT_KEY)
        claims = dict(token_obj.claims)
        # Validate expiry: exp is a Unix timestamp integer in joserfc
        now_ts = int(datetime.now(timezone.utc).timestamp())
        if claims.get("exp", 0) < now_ts:
            return None
        return claims
    except Exception:
        return None


_PROVIDER_SCOPES: dict[OAuthProvider, list[str]] = {
    OAuthProvider.GOOGLE: ["openid", "email", "profile"],
    OAuthProvider.GITHUB: ["read:user", "user:email", "repo"],
    OAuthProvider.LINKEDIN: ["openid", "profile", "email"],
    OAuthProvider.APPLE: ["openid", "email", "name"],
    OAuthProvider.MICROSOFT: ["openid", "email", "profile", "User.Read"],
    OAuthProvider.DISCORD: ["identify", "email"],
}

_AUTH_ENDPOINTS: dict[OAuthProvider, str] = {
    OAuthProvider.GOOGLE: "https://accounts.google.com/o/oauth2/v2/auth",
    OAuthProvider.GITHUB: "https://github.com/login/oauth/authorize",
    OAuthProvider.LINKEDIN: "https://www.linkedin.com/oauth/v2/authorization",
    OAuthProvider.APPLE: "https://appleid.apple.com/auth/authorize",
    OAuthProvider.MICROSOFT: "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
    OAuthProvider.DISCORD: "https://discord.com/oauth2/authorize",
}


def oauth_provider_configs(
    *,
    enabled_providers: tuple[str, ...],
    redirect_base_url: str,
) -> list[OAuthProviderConfig]:
    enabled = {provider.lower() for provider in enabled_providers}
    configs: list[OAuthProviderConfig] = []
    for provider in OAuthProvider:
        callback = f"{redirect_base_url.rstrip('/')}/{provider.value}/callback"
        client_id = os.getenv(f"{provider.value.upper()}_CLIENT_ID", "")
        configs.append(
            OAuthProviderConfig(
                provider=provider,
                enabled=provider.value in enabled and bool(client_id),
                authorization_url=_AUTH_ENDPOINTS[provider] if client_id else None,
                callback_url=callback,
                scopes=_PROVIDER_SCOPES[provider],
            )
        )
    return configs


def protect_refresh_token(token: str | None) -> str | None:
    if not token:
        return None
    digest = hmac.new(_JWT_SECRET_RAW.encode(), token.encode(), hashlib.sha256).hexdigest()
    return f"hmac-sha256:{digest}"


def infer_provider_intelligence(
    *,
    provider: OAuthProvider,
    metadata: dict,
) -> ProviderIntelligence:
    now = datetime.now(timezone.utc)
    if provider == OAuthProvider.GITHUB:
        languages = metadata.get("languages", {})
        repos = metadata.get("repositories", [])
        backend_signal = _language_score(languages, {"Python", "Go", "Java", "Rust", "SQL"})
        frontend_signal = _language_score(languages, {"JavaScript", "TypeScript", "CSS", "HTML"})
        architecture = min(
            1.0,
            (
                _metadata_term_count(repos, {"api", "service", "distributed", "docker", "infra"})
                + len(repos) * 0.03
            ),
        )
        return ProviderIntelligence(
            provider=provider,
            signals={
                "backend_tendency": round(backend_signal, 4),
                "frontend_tendency": round(frontend_signal, 4),
                "engineering_depth": round(min(1.0, architecture + backend_signal * 0.25), 4),
                "architecture_maturity": round(architecture, 4),
            },
            summary="GitHub metadata mapped into engineering tendency and architecture signals.",
            evidence=[f"{len(repos)} repositories observed", f"{len(languages)} language signals observed"],
            updated_at=now,
        )
    if provider == OAuthProvider.LINKEDIN:
        positions = metadata.get("positions", [])
        industries = metadata.get("industries", [])
        seniority = min(1.0, len(positions) / 5)
        progression = min(1.0, _metadata_term_count(positions, {"lead", "senior", "manager", "architect"}) / 4)
        return ProviderIntelligence(
            provider=provider,
            signals={
                "experience_level": round(seniority, 4),
                "role_progression": round(progression, 4),
                "industry_specialization": round(min(1.0, len(set(industries)) / 4), 4),
            },
            summary="LinkedIn metadata mapped into experience, progression, and industry specialization.",
            evidence=[f"{len(positions)} positions observed", f"{len(set(industries))} industries observed"],
            updated_at=now,
        )
    return ProviderIntelligence(
        provider=provider,
        signals={"identity_confidence": 0.6 if metadata else 0.2},
        summary="Provider linked; no specialized intelligence extractor available yet.",
        evidence=["Provider account is linked to the unified identity graph."],
        updated_at=now,
    )


def _language_score(languages: dict, selected: set[str]) -> float:
    total = sum(float(value) for value in languages.values()) or 1.0
    selected_total = sum(float(value) for key, value in languages.items() if key in selected)
    return min(1.0, selected_total / total)


def _metadata_term_count(items: list, terms: set[str]) -> float:
    text = " ".join(str(item).lower() for item in items)
    return float(sum(1 for term in terms if term in text))
