"""Sandbox-only side channel (§9 tests 3-7) — the dummy payer won't act on a submitted
preauth/claim on its own; this tells it what to do so it fires the matching on_submit/request
callback. Not part of the real NHCX protocol, never called against a real payer.

Field names confirmed against the "NHCX Dummy Payer Implementation" doc's curl examples and
a live sandbox call (20 Jul 2026): process/request wants camelCase "correlationId", not
snake_case "correlation_id" — sending the wrong key gets an unhandled 500 from their side,
not a clean validation error.
"""
import logging
import time

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


def _responseBody(response: httpx.Response) -> dict | str:
    if not response.content:
        return {}
    try:
        return response.json()
    except Exception:
        return response.text


def _raiseForSandboxError(response: httpx.Response) -> None:
    if response.status_code < 400:
        return
    raise Exception(f"dummy payer returned HTTP {response.status_code}: {_responseBody(response)}")


def _shouldRetryProcess(response: httpx.Response, action: DummyPayerAction, method: DummyPayerMethod) -> bool:
    if response.status_code >= 500:
        return True
    # Query/Preauth is eventually consistent in the sandbox: the same correlation id can 400
    # immediately after /preauth/submit and dispatch successfully once the dummy payer catches up.
    return response.status_code == 400 and action == DummyPayerAction.QUERY and method == DummyPayerMethod.PREAUTH


class DummyPayerService:
    def processRequest(self, correlationId: str, action: DummyPayerAction, method: DummyPayerMethod) -> dict:
        body = {"correlationId": correlationId, "action": action.value, "method": method.value}
        response = None
        for attempt in range(1, 5):
            response = httpx.post(
                f"{settings.nhcxDummyPayerBase}{DummyPayerEndpoint.PROCESS_REQUEST.value}",
                json=body,
                headers=_headers(),
                timeout=30,
            )
            logger.info(
                "dummy payer process/request correlationId=%s action=%s method=%s attempt=%s -> %s",
                correlationId, action, method, attempt, response.status_code,
            )
            if not _shouldRetryProcess(response, action, method):
                break
            if attempt < 4:
                # The sandbox can 500 briefly while the queued request becomes visible.
                time.sleep(8)
        _raiseForSandboxError(response)
        return response.json()

    def paymentNoticeInit(self, correlationId: str) -> dict:
        response = httpx.post(
            f"{settings.nhcxDummyPayerBase}{DummyPayerEndpoint.PAYMENT_NOTICE_INIT.value}",
            json={"correlation_id": correlationId, "providerId": settings.nhcxParticipantCode},
            headers=_headers(),
            timeout=30,
        )
        _raiseForSandboxError(response)
        return response.json()


dummyPayerService = DummyPayerService()
