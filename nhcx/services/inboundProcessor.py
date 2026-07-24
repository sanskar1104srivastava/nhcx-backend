"""Actual inbound work (decrypt/validate/store) — runs after the ack, off the SQS queue (§5b).
Shared by the API Lambda's local-dev fallback and the SQS consumer Lambda.

Two different inbound shapes, handled separately (§10):
  - Domain messages (on_check/on_submit/request/etc.) — JWE-encrypted, body is {"payload": jwe}.
  - Protocol-level events (/v1/error, and any explicit-reject ProtocolResponse) — plain JSON,
    no "payload" key, carries an error code directly. Treating both the same way was a bug:
    the mandatory /v1/error endpoint would KeyError on rawBody["payload"].
"""
import logging

from nhcx.config import settings
from nhcx.constants import Direction, LogState, UseCase
from nhcx import errorCodes
from nhcx.services.dbService import dbService
from nhcx.services.certService import certService
from nhcx.services.keyService import getPrivateKeyPem
from nhcx.utils.cryptoUtils import peekProtectedHeader, decryptPayload
from nhcx.utils.piiMaskUtil import maskPii

logger = logging.getLogger(__name__)


def processInboundMessage(rawBody: dict, entityType: UseCase, hospitalId: str) -> None:
    if "payload" not in rawBody:
        _processProtocolEvent(rawBody)
        return

    header = peekProtectedHeader(rawBody["payload"])
    apiCallId = header.get("x-hcx-api_call_id", "")
    correlationId = header.get("x-hcx-correlation_id", "")
    senderCode = header.get("x-hcx-sender_code", "")

    existing = dbService.findByApiCallId(apiCallId)
    if existing is not None:
        logger.info("Duplicate inbound retry for apiCallId=%s — already processed, skipping", apiCallId)
        return

    if not settings.skipSenderValidation and not certService.isKnownParticipant(senderCode):
        # §11 — JWE alone doesn't authenticate the sender; reject/quarantine anything from an
        # unrecognized participant rather than trusting it blindly.
        logger.error("Rejecting inbound message from unrecognized sender_code=%s apiCallId=%s", senderCode, apiCallId)
        dbService.insertLog(
            hospitalId=hospitalId, useCase=entityType.value, direction=Direction.INBOUND.value,
            correlationId=correlationId, apiCallId=apiCallId, requestId=header.get("x-hcx-request_id", ""),
            workflowId=header.get("x-hcx-workflow_id", ""), senderCode=senderCode,
            recipientCode=header.get("x-hcx-recipient_code", ""), xHcxStatus=header.get("x-hcx-status", ""),
            state=LogState.ERROR.value, errorMessage="unrecognized sender_code — quarantined",
        )
        return

    decrypted = decryptPayload(rawBody["payload"], getPrivateKeyPem())
    entry = dbService.insertLog(
        hospitalId=hospitalId,
        useCase=entityType.value,
        direction=Direction.INBOUND.value,
        correlationId=correlationId,
        apiCallId=apiCallId,
        requestId=header.get("x-hcx-request_id", ""),
        workflowId=header.get("x-hcx-workflow_id", ""),
        senderCode=senderCode,
        recipientCode=header.get("x-hcx-recipient_code", ""),
        xHcxStatus=header.get("x-hcx-status", ""),
        fhirBundleIn=decrypted,
        jweIn=rawBody["payload"],
        benAbhaId=header.get("x-hcx-ben-abha-id") or None,
    )
    dbService.updateState(entry, LogState.RESPONDED_COMPLETE)


def _processProtocolEvent(rawBody: dict) -> None:
    """/v1/error and explicit protocol-level rejections — no JWE, error code in the body directly.
    NHCX permanently kills the correlation_id after 5 failed retries; mirror that by marking
    every log entry in the cycle DEAD (§5b/§8)."""
    correlationId = rawBody.get("correlation_id") or rawBody.get("x-hcx-correlation_id", "")
    errorCode = rawBody.get("error", {}).get("code", "") or rawBody.get("x-hcx-error_details", {}).get("code", "")
    logger.error("Protocol-level event correlationId=%s errorCode=%s body=%s", correlationId, errorCode, maskPii(str(rawBody)))

    classification = errorCodes.classify(errorCode)
    if classification == "protocol_bug":
        logger.error("ALERT: %s — our own id generation collided, this is a bug on our side", errorCode)
    elif classification == "stale_cert":
        senderCode = rawBody.get("sender_code") or rawBody.get("x-hcx-sender_code", "")
        if senderCode:
            certService.invalidateCache(senderCode)

    if not correlationId:
        return
    for item in dbService.findByCorrelationId(correlationId):
        dbService.updateState(item, LogState.DEAD, errorCode=errorCode, errorMessage=str(rawBody.get("error", {}).get("message", "")))
