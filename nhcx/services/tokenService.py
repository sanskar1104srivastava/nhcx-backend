"""Auth (§2) — cache the token, refresh at ~80%, retry once on 401."""
import logging
import time

import httpx

from nhcx.config import settings
from nhcx.constants import TOKEN_REFRESH_FRACTION, ACCEPT_HEADER, CONTENT_TYPE_HEADER, APPLICATION_JSON

logger = logging.getLogger(__name__)


class TokenService:
    def __init__(self) -> None:
        self._accessToken: str | None = None
        self._refreshToken: str | None = None
        self._expiresAt: float = 0.0

    def _fetchNewToken(self) -> None:
        logger.info("Fetching new NHCX access token")
        response = httpx.post(
            settings.abdmSessionsUrl,
            json={"clientId": settings.nhcxClientId, "clientSecret": settings.nhcxClientSecret},
            headers={ACCEPT_HEADER: APPLICATION_JSON, CONTENT_TYPE_HEADER: APPLICATION_JSON},
            timeout=30,
        )
        response.raise_for_status()
        body = response.json()
        self._accessToken = body["accessToken"]
        self._refreshToken = body.get("refreshToken")
        self._expiresAt = time.monotonic() + body["expiresIn"] * TOKEN_REFRESH_FRACTION

    def getToken(self, forceRefresh: bool = False) -> str:
        if forceRefresh or self._accessToken is None or time.monotonic() >= self._expiresAt:
            self._fetchNewToken()
        return self._accessToken

    def bearerHeaderValue(self) -> str:
        return f"Bearer {self.getToken()}"


tokenService = TokenService()
