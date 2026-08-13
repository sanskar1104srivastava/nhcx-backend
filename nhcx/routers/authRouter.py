"""Session-based auth — username/password login returns a session token.
The admin key is stored per-user in DynamoDB and injected into NHCX calls."""
import logging
import secrets
import time
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel
from nhcx.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])

# In-memory session store (swap for DynamoDB in production)
_sessions: dict[str, dict] = {}  # token -> { username, adminKey, createdAt }
_USER_ADMIN_KEY = settings.adminApiKey  # single admin key for now

# Default credentials — override via env vars in production
_DEFAULT_USERNAME = "admin"
_DEFAULT_PASSWORD = "nhcx@123"


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    ok: bool
    token: str
    username: str


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest):
    if body.username != _DEFAULT_USERNAME or body.password != _DEFAULT_PASSWORD:
        raise HTTPException(401, "Invalid username or password")

    token = secrets.token_urlsafe(32)
    _sessions[token] = {
        "username": body.username,
        "adminKey": _USER_ADMIN_KEY,
        "createdAt": time.time(),
    }
    logger.info("User '%s' logged in", body.username)
    return LoginResponse(ok=True, token=token, username=body.username)


@router.post("/logout")
def logout(authorization: str | None = Header(default=None)):
    token = _extract_token(authorization)
    if token and token in _sessions:
        del _sessions[token]
    return {"ok": True}


@router.get("/me")
def me(authorization: str | None = Header(default=None)):
    token = _extract_token(authorization)
    if not token or token not in _sessions:
        raise HTTPException(401, "Not authenticated")
    session = _sessions[token]
    return {"ok": True, "username": session["username"]}


def _extract_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    if authorization.startswith("Bearer "):
        return authorization[7:]
    return authorization


def get_admin_key_from_token(authorization: str | None) -> str | None:
    """Extract admin key from session token. Used by middleware."""
    token = _extract_token(authorization)
    if not token:
        return None
    session = _sessions.get(token)
    if not session:
        return None
    return session.get("adminKey")
