"""Generic outbound sender (§4, §5a) — every use case in §5a routes through send()."""
import logging

import httpx

from nhcx.config import settings
from nhcx.constants import (
    Direction, LogState, HcxStatus, StatusPreset,
    Header, ACCEPT_HEADER, CONTENT_TYPE_HEADER, APPLICATION_JSON, BEARER_AUTH_HEADER,
    PAYLOAD_KEY, OutboundEndpoint, UseCase,
)
from nhcx.requests.outboundRequest import OutboundRequest
from nhcx.services.tokenService import tokenService
from nhcx.services.certService import certService
from nhcx.services.dbService import dbService
from nhcx.utils.idUtils import newUuid
from nhcx.utils.timeUtils import formatHcxTimestamp
from nhcx.utils.cryptoUtils import encryptPayload
from nhcx.utils.certPemUtils import wrapCertB64AsPem
from nhcx.utils.piiMaskUtil import maskPii
from nhcx.utils.bundleValidator import validateBundle
from nhcx import errorCodes

logger = logging.getLogger(__name__)

_INITIAL_STATUS = HcxStatus.REQUEST_INITIATED.value if settings.nhcxStatusPreset == StatusPreset.INITIATED.value else HcxStatus.REQUEST_INITIATE.value

# Confirmed via real sandbox testing: reply-style endpoints (on_request/on_submit — where WE are
# completing something THEY asked us for, not starting a fresh cycle) need x-hcx-status =
# response.complete. Sending the request-initiating status here got NHCX-1011 "Invalid Status".
_REPLY_ENDPOINTS = {OutboundEndpoint.COMMUNICATION_REPLY, OutboundEndpoint.PAYMENT_NOTICE_ACK}


def _statusForEndpoint(endpoint: OutboundEndpoint) -> str:
    return HcxStatus.RESPONSE_COMPLETE.value if endpoint in _REPLY_ENDPOINTS else _INITIAL_STATUS


def _buildProtectedHeader(req: OutboundRequest, apiCallId: str, requestId: str, correlationId: str) -> dict:
    logger.info("Building envelope with statusPreset=%s timestampPreset=%s", settings.nhcxStatusPreset, settings.nhcxTimestampPreset)
    return {
        Header.API_CALL_ID.value: apiCallId,
        Header.WORKFLOW_ID.value: req.workflowId,
        Header.REQUEST_ID.value: requestId,
        Header.STATUS.value: _statusForEndpoint(req.endpoint),
        Header.TIMESTAMP.value: formatHcxTimestamp(),
        Header.SENDER_CODE.value: settings.nhcxParticipantCode,
        Header.RECIPIENT_CODE.value: req.recipientCode,
        Header.CORRELATION_ID.value: correlationId,
        Header.BEN_ABHA_ID.value: req.benAbhaId or "",
    }


def _postWithRetry(endpoint: str, jwePayload: str, includeTypeField: bool = False) -> httpx.Response:
    """One POST + one 401-triggered token-refresh retry, shared by every outbound call.
    Confirmed via real sandbox testing, the hard way: reply-style endpoints (on_request/on_submit)
    need "type": "JWEPayload" alongside "payload" in the outer envelope, or the gateway rejects it
    with a generic "Failed to read request" — but adding that same field to the initiating
    endpoints (check/submit) breaks THEM instead. The two families genuinely want different bodies."""
    body = {PAYLOAD_KEY: jwePayload}
    if includeTypeField:
        body = {"type": "JWEPayload", **body}
    kwargs = dict(url=f"{settings.nhcxGatewayBase}{endpoint}", json=body, timeout=30)
    response = httpx.post(
        headers={ACCEPT_HEADER: APPLICATION_JSON, CONTENT_TYPE_HEADER: APPLICATION_JSON, BEARER_AUTH_HEADER: tokenService.bearerHeaderValue()},
        **kwargs,
    )
    if response.status_code == 401:
        response = httpx.post(
            headers={ACCEPT_HEADER: APPLICATION_JSON, CONTENT_TYPE_HEADER: APPLICATION_JSON, BEARER_AUTH_HEADER: f"Bearer {tokenService.getToken(forceRefresh=True)}"},
            **kwargs,
        )
    return response


class HcxApiService:
    def send(self, req: OutboundRequest) -> dict:
        validateBundle(req.fhirBundle)  # §7 — nothing leaves unvalidated

        apiCallId = newUuid()
        requestId = newUuid()
        correlationId = req.correlationId or newUuid()

        if req.correlationId:  # a dead correlation_id must never be reused (§4c) — enforce it, don't just document it
            for priorEntry in dbService.findByCorrelationId(req.correlationId):
                if priorEntry.state == LogState.DEAD.value:
                    raise ValueError(f"correlation_id {req.correlationId} is dead — a retry must use a fresh UUID, never the same one")

        recipientCert = certService.getCachedPayerCert(req.recipientCode)
        protectedHeader = _buildProtectedHeader(req, apiCallId, requestId, correlationId)
        jwePayload = encryptPayload(req.fhirBundle, wrapCertB64AsPem(recipientCert["encryption_cert"]), protectedHeader)

        entry = None
        body = None
        try:
            entry = dbService.insertLog(
                hospitalId=req.hospitalId,
                useCase=req.useCase.value,
                direction=Direction.OUTBOUND.value,
                correlationId=correlationId,
                apiCallId=apiCallId,
                requestId=requestId,
                workflowId=req.workflowId,
                senderCode=settings.nhcxParticipantCode,
                recipientCode=req.recipientCode,
                xHcxStatus=_statusForEndpoint(req.endpoint),
                fhirBundleOut=req.fhirBundle,
                jweOut=jwePayload,
                benAbhaId=req.benAbhaId,
                claimNumber=req.claimNumber,
                policyNumber=req.policyNumber,
            )
            response = _postWithRetry(req.endpoint.value, jwePayload, includeTypeField=req.endpoint in _REPLY_ENDPOINTS)
            body = response.json() if response.content else {}
            errorCode = (body.get("error") or {}).get("code", "")  # sandbox sends "error": null on success, not {}
            if errorCode in errorCodes.STALE_CERT_ERROR_CODES:  # §3 — cached recipient cert is stale
                logger.warning("%s on send to %s — invalidating cached cert and re-raising", errorCode, req.recipientCode)
                certService.invalidateCache(req.recipientCode)

            response.raise_for_status()
            protocolStatus = (body.get("result") or {}).get("protocol_status")  # nested under "result", not top-level
            dbService.updateState(entry, LogState.ACKED, protocolStatus=protocolStatus)
            return body
        except Exception as exc:
            detail = f"{exc} — response body: {body}" if body is not None else str(exc)
            logger.error("Outbound send failed correlationId=%s: %s", correlationId, maskPii(detail))
            if entry is not None:
                dbService.updateState(entry, LogState.ERROR, errorMessage=detail)
            raise

    def checkStatus(self, hospitalId: str, recipientCode: str, targetCorrelationId: str) -> dict:
        """Status check (§5a) — protocol-level, no domain FHIR bundle to validate/store, just
        the envelope. Confirmed via real sandbox testing: NHCX looks this up by x-hcx-api_call_id
        of the ORIGINAL request being asked about, not a fresh one minted for this status-check
        message — sending a fresh id here gets NHCX-1012 "No records found with the requested
        api caller id" every time."""
        priorEntries = [e for e in dbService.findByCorrelationId(targetCorrelationId) if e.useCase != UseCase.STATUS.value]
        if not priorEntries:
            raise ValueError(f"no prior request logged for correlation_id {targetCorrelationId} — nothing to check status on")
        originalApiCallId = min(priorEntries, key=lambda e: e.createdAt).apiCallId

        apiCallId = newUuid()
        requestId = newUuid()

        recipientCert = certService.getCachedPayerCert(recipientCode)
        protectedHeader = {
            Header.API_CALL_ID.value: originalApiCallId,
            Header.WORKFLOW_ID.value: "13",
            Header.REQUEST_ID.value: requestId,
            Header.STATUS.value: _INITIAL_STATUS,
            Header.TIMESTAMP.value: formatHcxTimestamp(),
            Header.SENDER_CODE.value: settings.nhcxParticipantCode,
            Header.RECIPIENT_CODE.value: recipientCode,
            Header.CORRELATION_ID.value: targetCorrelationId,
            Header.BEN_ABHA_ID.value: "",
        }
        jwePayload = encryptPayload({}, wrapCertB64AsPem(recipientCert["encryption_cert"]), protectedHeader)

        entry = dbService.insertLog(
            hospitalId=hospitalId, useCase=UseCase.STATUS.value, direction=Direction.OUTBOUND.value,
            correlationId=targetCorrelationId, apiCallId=apiCallId, requestId=requestId, workflowId="13",
            senderCode=settings.nhcxParticipantCode, recipientCode=recipientCode, xHcxStatus=_INITIAL_STATUS,
            jweOut=jwePayload,
        )
        try:
            response = _postWithRetry(OutboundEndpoint.STATUS.value, jwePayload)
            body = response.json() if response.content else {}
            response.raise_for_status()
            protocolStatus = (body.get("result") or {}).get("protocol_status")
            dbService.updateState(entry, LogState.ACKED, protocolStatus=protocolStatus)
            return body
        except Exception as exc:
            detail = f"{exc} — response body: {exc.response.text}" if isinstance(exc, httpx.HTTPStatusError) else str(exc)
            logger.error("Status check failed correlationId=%s: %s", targetCorrelationId, maskPii(detail))
            dbService.updateState(entry, LogState.ERROR, errorMessage=detail)
            raise

    def sendRejection(self, endpointPath: str, protocolResponseBody: dict, correlationId: str) -> dict:
        """Sends a plain (unencrypted) ProtocolResponse rejection to the given on_request/on_submit
        path — the "reject after evaluation" alternative to ack-then-process (§5b, low priority)."""
        response = httpx.post(
            f"{settings.nhcxGatewayBase}{endpointPath}",
            json=protocolResponseBody,
            headers={ACCEPT_HEADER: APPLICATION_JSON, CONTENT_TYPE_HEADER: APPLICATION_JSON, BEARER_AUTH_HEADER: tokenService.bearerHeaderValue()},
            timeout=30,
        )
        body = response.json() if response.content else {}
        response.raise_for_status()
        logger.info("Sent rejection ProtocolResponse for correlationId=%s -> %s", correlationId, response.status_code)
        return body


hcxApiService = HcxApiService()
