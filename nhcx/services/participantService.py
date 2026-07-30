"""Participant Service (§6) — plain JSON, no JWE, unlike the gateway use-case APIs.
We only ever call get/policies (read) in production; link/delink is a one-off test-harness
utility for standing in as "the payer" in sandbox, not a production endpoint we build around.
"""
import logging

import httpx

from nhcx.config import settings
from nhcx.constants import (
    ACCEPT_HEADER, CONTENT_TYPE_HEADER, APPLICATION_JSON, BEARER_AUTH_HEADER,
    ParticipantEndpoint, PolicyIdentifierType, ParticipantRole,
)
from nhcx.services.tokenService import tokenService

logger = logging.getLogger(__name__)


def _headers() -> dict:
    return {
        ACCEPT_HEADER: APPLICATION_JSON,
        CONTENT_TYPE_HEADER: APPLICATION_JSON,
        BEARER_AUTH_HEADER: tokenService.bearerHeaderValue(),
    }


def _raiseForNhcxError(response: httpx.Response) -> None:
    if response.status_code < 400:
        return
    body = response.json() if response.content else {}
    nhcxError = body.get("error") or {}
    code = nhcxError.get("code", "")
    message = nhcxError.get("message", "")
    if code:
        raise Exception(f"NHCX {code}: {message}")
    response.raise_for_status()


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
        _raiseForNhcxError(response)
        return response.json()

    def listParticipants(self, role: ParticipantRole, fromDate: str, toDate: str) -> dict:
        """Read-only participant registry lookup from the sandbox Participant Service docs."""
        response = httpx.post(
            f"{settings.nhcxParticipantBase}{ParticipantEndpoint.PARTICIPANTS_LIST.value}",
            json={"role": role.value, "fromdate": fromDate, "todate": toDate},
            headers=_headers(),
            timeout=30,
        )
        _raiseForNhcxError(response)
        return response.json()

    def linkPolicy(
        self, abhaNumber: str, mobileNumber: str, memberId: str, payerId: str,
        processingId: str, policies: list[dict], requestId: str | None = None,
    ) -> dict:
        """Test-harness only — production policy linking is the insurer/TPA's job, not ours (§6)."""
        import uuid
        response = httpx.post(
            f"{settings.nhcxParticipantBase}{ParticipantEndpoint.LINK_POLICY.value}",
            json={
                "requestid": requestId or str(uuid.uuid4()), "abhanumber": abhaNumber, "mobilenumber": mobileNumber,
                "memberid": memberId, "payerid": payerId, "processingid": processingId, "policies": policies,
            },
            headers=_headers(),
            timeout=30,
        )
        _raiseForNhcxError(response)
        return response.json()

    def delinkPolicy(
        self, memberId: str, payerId: str, processingId: str, policies: list[dict],
        requestId: str | None = None,
    ) -> dict:
        """Test-harness only — removes a sandbox ABHA-policy link for the supplied payer/product."""
        import uuid
        response = httpx.post(
            f"{settings.nhcxParticipantBase}{ParticipantEndpoint.DELINK_POLICY.value}",
            json={
                "requestid": requestId or str(uuid.uuid4()), "memberid": memberId,
                "payerid": payerId, "processingid": processingId, "policies": policies,
            },
            headers=_headers(),
            timeout=30,
        )
        _raiseForNhcxError(response)
        return response.json()


participantService = ParticipantService()
