"""Inbound (§5b) — NHCX calls us. Ack first (202, exact shape, <~500ms), then decrypt/store.

Real work is enqueued to SQS before acking, not run inline: on Lambda + API Gateway, work
started after the response is sent can be frozen mid-flight when the invocation ends — the
exact failure mode a sibling project hit (~40% of callbacks lost to throttling). A separate
consumer Lambda (nhcx/consumer.py), triggered by the queue, does the decrypt/store.
"""
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Request, Response, status

from nhcx.config import settings
from nhcx.constants import UseCase
from nhcx.responses.ackResponse import AckResponse
from nhcx.services.awsService import awsService
from nhcx.services.inboundProcessor import processInboundMessage
from nhcx.utils.cryptoUtils import peekProtectedHeader

logger = logging.getLogger(__name__)
router = APIRouter()

_BASE_ENTITY_TYPE_BY_PATH = {
    "/insuranceplan/on_request": UseCase.INSURANCE_PLAN,
    "/coverageeligibility/on_check": UseCase.COVERAGE_ELIGIBILITY,
    "/preauth/on_submit": UseCase.PREAUTH,
    "/claim/on_submit": UseCase.CLAIM,
    "/communication/request": UseCase.COMMUNICATION,
    "/paymentnotice/request": UseCase.PAYMENT,
    "/task/on_submit": UseCase.TASK,
    "/on_status": UseCase.STATUS,
    "/v1/error": UseCase.STATUS,   # mandatory: fires when our outbound delivery died after 5 retries
}

# Confirmed via real sandbox traffic: NHCX actually calls back on a /v1/-prefixed path
# (e.g. /v1/preauth/on_submit), not the bare path the requirements doc listed — this was the
# real reason every callback silently 404'd. Registering both so neither convention breaks us.
_ENTITY_TYPE_BY_PATH = {
    **_BASE_ENTITY_TYPE_BY_PATH,
    **{f"/v1{path}": entity for path, entity in _BASE_ENTITY_TYPE_BY_PATH.items() if not path.startswith("/v1")},
}


async def handleInbound(request: Request, response: Response, background: BackgroundTasks) -> dict:
    path = request.url.path
    entityType = _ENTITY_TYPE_BY_PATH.get(path, UseCase.STATUS)
    rawBody = await request.json()

    if "payload" in rawBody:
        header = peekProtectedHeader(rawBody["payload"])
        apiCallId = header.get("x-hcx-api_call_id", "")
        correlationId = header.get("x-hcx-correlation_id", "")
        senderCode = header.get("x-hcx-sender_code", "")
    else:
        # /v1/error and other protocol-level events aren't JWE-wrapped — the real ProtocolResponse
        # schema uses top-level x-hcx-* prefixed keys (confirmed from NHA's own error-handling
        # doc), not bare snake_case — reading the wrong keys here silently echoed empty ids back.
        apiCallId = rawBody.get("x-hcx-api_call_id", "")
        correlationId = rawBody.get("x-hcx-correlation_id", "")
        senderCode = rawBody.get("x-hcx-sender_code", "")

    if settings.inboundQueueUrl:
        awsService.sendQueueMessage(
            settings.inboundQueueUrl,
            json.dumps({"rawBody": rawBody, "entityType": entityType.value, "hospitalId": settings.nhcxParticipantCode}),
        )
    else:
        # No queue configured (local dev, off Lambda) — BackgroundTasks runs this *after* the
        # response is sent, so a processing failure (bad key, decrypt error, etc.) can never
        # block the mandatory ack. Only safe because this branch never runs on Lambda — Lambda
        # deployments always set INBOUND_QUEUE_URL (see serverless.yml) and take the SQS path.
        background.add_task(processInboundMessage, rawBody, entityType, settings.nhcxParticipantCode)

    response.status_code = status.HTTP_202_ACCEPTED
    return AckResponse.build(
        apiCallId=apiCallId,
        correlationId=correlationId,
        senderCode=senderCode,
        recipientCode=settings.nhcxParticipantCode,
        entityType=entityType,
    ).model_dump()


for _path in _ENTITY_TYPE_BY_PATH:
    router.add_api_route(_path, handleInbound, methods=["POST"])
