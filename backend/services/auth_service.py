from datetime import datetime, timedelta, timezone
from passlib.hash import argon2
from authlib.jose import jwt
from authlib.jose.errors import JoseError
import os
import uuid

# In a real system, these would be loaded from Settings/Env
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret-key-do-not-use-in-prod")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

def get_password_hash(password: str) -> str:
    return argon2.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return argon2.verify(plain_password, hashed_password)

def create_access_token(subject: str) -> str:
    now = datetime.now(timezone.utc)
    header = {"alg": JWT_ALGORITHM}
    payload = {
        "sub": subject,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": now,
        "jti": str(uuid.uuid4())
    }
    return jwt.encode(header, payload, JWT_SECRET_KEY).decode('utf-8')

def create_refresh_token() -> str:
    return str(uuid.uuid4())

def verify_access_token(token: str) -> dict | None:
    try:
        claims = jwt.decode(token, JWT_SECRET_KEY)
        claims.validate()
        return claims
    except JoseError:
        return None
