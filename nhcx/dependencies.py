"""Shared FastAPI dependencies."""
from fastapi import Header, HTTPException
from nhcx.config import settings


def requireAdminKey(
    x_admin_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    """Gates admin/dev-tool routes. Accepts either:
    1. X-Admin-Key header (direct API key)
    2. Authorization: Bearer <session_token> (from /auth/login)
    No-op if ADMIN_API_KEY isn't configured (local dev)."""
    if not settings.adminApiKey:
        return

    # Check direct admin key first
    if x_admin_key and x_admin_key == settings.adminApiKey:
        return

    # Check session token
    if authorization:
        from nhcx.routers.authRouter import get_admin_key_from_token
        key = get_admin_key_from_token(authorization)
        if key and key == settings.adminApiKey:
            return

    raise HTTPException(401, "missing or invalid authentication")
