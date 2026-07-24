"""Sandbox-only side channel (§9 tests 3-7) — the dummy payer won't act on a submitted
preauth/claim on its own; this tells it what to do so it fires the matching on_submit/request
callback. Not part of the real NHCX protocol, never called against a real payer.

Field names confirmed against the "NHCX Dummy Payer Implementation" doc's curl examples and
a live sandbox call (20 Jul 2026): process/request wants camelCase "correlationId", not
snake_case "correlation_id" — sending the wrong key gets an unhandled 500 from their side,
not a clean validation error.
"""
import logging

import httpx

from nhcx.config import settings
from nhcx.constants import (
    ACCEPT_HEADER, CONTENT_TYPE_HEADER, APPLICATION_JSON, BEARER_AUTH_HEADER,
    DummyPayerEndpoint, DummyPayerAction, DummyPayerMethod,
)
from nhcx.services.tokenService import tokenService

logger = logging.getLogger(__name__)


def _headers() -> dict:
    return {
        ACCEPT_HEADER: APPLICATION_JSON,
        CONTENT_TYPE_HEADER: APPLICATION_JSON,
        BEARER_AUTH_HEADER: tokenService.bearerHeaderValue(),
    }


class DummyPayerService:
    def processRequest(self, correlationId: str, action: DummyPayerAction, method: DummyPayerMethod) -> dict:
        response = httpx.post(
            f"{settings.nhcxDummyPayerBase}{DummyPayerEndpoint.PROCESS_REQUEST.value}",
            json={"correlationId": correlationId, "action": action.value, "method": method.value},
            headers=_headers(),
            timeout=30,
        )
        logger.info("dummy payer process/request correlationId=%s action=%s method=%s -> %s", correlationId, action, method, response.status_code)
        response.raise_for_status()
        return response.json()

    def paymentNoticeInit(self, correlationId: str) -> dict:
        response = httpx.post(
            f"{settings.nhcxDummyPayerBase}{DummyPayerEndpoint.PAYMENT_NOTICE_INIT.value}",
            json={"correlation_id": correlationId},
            headers=_headers(),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()


dummyPayerService = DummyPayerService()
