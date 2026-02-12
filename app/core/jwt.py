from datetime import datetime, timedelta
import uuid
from jose import jwt, JWTError
from uuid import UUID
from app.core.config import Config
from app.core.request_context import AuthStatus

SECRET_KEY = Config.JWT_SECRET or "SUPER_SECRET_KEY"
ALGORITHM = Config.JWT_ALGORITHM or "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = Config.ACCESS_TOKEN_EXPIRE_MINUTES
ANONYMOUS_TOKEN_EXPIRE_MINUTES = Config.ANONYMOUS_TOKEN_EXPIRE_MINUTES


def create_access_token(
    user_id: UUID,
    role: str,
    token_version: int,
    username: str
):
    payload = {
        "sub": str(user_id),
        "roles": role,
        "token_version": str(token_version),
        "type": role,
        "user_id": str(user_id),
        "auth_status": AuthStatus.AUTHENTICATED.value,
        "username": username,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(
    user_id: UUID,
    token_version: int,
    role: str,
):
    payload = {
        "sub": str(user_id),
        "token_version": str(token_version),
        "type": role,
        "roles": role,
        "userId": str(user_id),
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=7),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_anonymous_token():
    unique_id = str(uuid.uuid4())
    payload = {
        "sub": unique_id,
        "type": AuthStatus.ANONYMOUS,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=ANONYMOUS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
