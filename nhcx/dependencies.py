"""Shared FastAPI dependencies."""
from fastapi import Header, HTTPException

from nhcx.config import settings


def requireAdminKey(x_admin_key: str | None = Header(default=None)) -> None:
    """Gates admin/dev-tool routes (§11). No-op if ADMIN_API_KEY isn't configured (local dev) —
    set it in the deployed environment to actually enforce this."""
    if not settings.adminApiKey:
        return
    if x_admin_key != settings.adminApiKey:
        raise HTTPException(401, "missing or invalid X-Admin-Key header")
