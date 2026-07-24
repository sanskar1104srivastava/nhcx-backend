"""Cert lifecycle (§3): self-check, register, fetch+cache payer certs."""
import logging
import time

import httpx

from nhcx.config import settings
from nhcx.constants import (
    ACCEPT_HEADER, CONTENT_TYPE_HEADER, APPLICATION_JSON, BEARER_AUTH_HEADER,
    ParticipantEndpoint,
)
from nhcx.services.tokenService import tokenService

logger = logging.getLogger(__name__)


def _headers() -> dict:
    return {
        ACCEPT_HEADER: APPLICATION_JSON,
        CONTENT_TYPE_HEADER: APPLICATION_JSON,
        BEARER_AUTH_HEADER: tokenService.bearerHeaderValue(),
    }


class CertService:
    def __init__(self) -> None:
        self._cache: dict[str, tuple[dict, float]] = {}  # participantId -> (response, expiresAtMonotonic)

    def fetchCerts(self, participantId: str) -> dict:
        """Test 0 — also used as our own self-check: empty/not-found means nothing registered yet (§3)."""
        response = httpx.post(
            f"{settings.nhcxParticipantBase}{ParticipantEndpoint.FETCH_CERTS.value}",
            json={"participantid": participantId},
            headers=_headers(),
            timeout=30,
        )
        logger.info("fetch/certs for %s -> %s", participantId, response.status_code)
        response.raise_for_status()
        return response.json()

    def getCachedPayerCert(self, participantId: str) -> dict:
        cached = self._cache.get(participantId)
        if cached and cached[1] > time.monotonic():
            return cached[0]
        result = self.fetchCerts(participantId)
        if not result.get("encryption_cert"):
            # sandbox returns HTTP 200 with null fields for an unregistered participant,
            # not a 404 — don't treat that as a valid cert, and don't cache the miss.
            raise ValueError(f"no cert registered for participant {participantId}")
        self._cache[participantId] = (result, time.monotonic() + settings.certCacheTtlSeconds)
        return result

    def isKnownParticipant(self, participantId: str) -> bool:
        """Inbound sender_code validation (§11) — a participant is 'known' if NHCX's own
        participant registry can produce a cert for them. Cheap because we cache the result
        either way, and we've usually already fetched the sender's cert before they call us back."""
        if not participantId:
            return False
        try:
            self.getCachedPayerCert(participantId)
            return True
        except Exception:
            return False

    def invalidateCache(self, participantId: str) -> None:
        """Call on PAYR-1001/1002 (stale cert) — see STALE_CERT_ERROR_CODES."""
        self._cache.pop(participantId, None)

    def registerOurCert(self, certificateB64SingleLine: str) -> dict:
        if "\n" in certificateB64SingleLine:
            raise ValueError("cert base64 must be a single line — wrapped base64 is a known cause of silent registration failures")
        response = httpx.post(
            f"{settings.nhcxParticipantBase}{ParticipantEndpoint.PARTICIPANT_UPDATE.value}",
            json={
                "participant_code": settings.nhcxParticipantCode,
                "encryption_cert": certificateB64SingleLine,
                "endpoint_url": settings.nhcxBridgeUrl,
            },
            headers=_headers(),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()


certService = CertService()
