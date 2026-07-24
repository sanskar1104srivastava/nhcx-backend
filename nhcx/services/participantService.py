"""Participant Service (§6) — plain JSON, no JWE, unlike the gateway use-case APIs.
We only ever call get/policies (read) in production; link/delink is a one-off test-harness
utility for standing in as "the payer" in sandbox, not a production endpoint we build around.
"""
import logging

import httpx

from nhcx.config import settings
from nhcx.constants import (
    ACCEPT_HEADER, CONTENT_TYPE_HEADER, APPLICATION_JSON, BEARER_AUTH_HEADER,
    ParticipantEndpoint, PolicyIdentifierType,
)
from nhcx.services.tokenService import tokenService

logger = logging.getLogger(__name__)


def _headers() -> dict:
    return {
        ACCEPT_HEADER: APPLICATION_JSON,
        CONTENT_TYPE_HEADER: APPLICATION_JSON,
        BEARER_AUTH_HEADER: tokenService.bearerHeaderValue(),
    }


class ParticipantService:
    def getPolicies(self, identifierType: PolicyIdentifierType, identifierValue: str) -> dict:
        """Returns payerid + processingid. processingid is the value to use as x-hcx-recipient_code
        for every message in this patient's claim journey when the payer sits under a TPA (§4c)."""
        response = httpx.post(
            f"{settings.nhcxParticipantBase}{ParticipantEndpoint.GET_POLICIES.value}",
            json={"identifiertype": identifierType.value, "identifiervalue": identifierValue},
            headers=_headers(),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def linkPolicy(self, abhaNumber: str, mobileNumber: str, memberId: str, payerId: str, processingId: str, policies: list[dict]) -> dict:
        """Test-harness only — production policy linking is the insurer/TPA's job, not ours (§6)."""
        import uuid
        response = httpx.post(
            f"{settings.nhcxParticipantBase}{ParticipantEndpoint.LINK_POLICY.value}",
            json={
                "requestid": str(uuid.uuid4()), "abhanumber": abhaNumber, "mobilenumber": mobileNumber,
                "memberid": memberId, "payerid": payerId, "processingid": processingId, "policies": policies,
            },
            headers=_headers(),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()


participantService = ParticipantService()
