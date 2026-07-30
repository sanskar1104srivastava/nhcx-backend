"""Dev-only endpoints wrapping participantService (§6) and the sandbox-only dummyPayerService
(§9 tests 3-7) — exposed so the admin frontend can drive them without a Python shell.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from nhcx.config import settings
from nhcx.constants import PolicyIdentifierType, ParticipantRole, DummyPayerAction, DummyPayerMethod, OutboundEndpoint, UseCase
from nhcx.dependencies import requireAdminKey
from nhcx.services.certService import certService
from nhcx.services.participantService import participantService
from nhcx.services.dummyPayerService import dummyPayerService
from nhcx.services.hcxApiService import hcxApiService
from nhcx.responses.protocolResponse import buildRejection
from nhcx.utils.idUtils import newUuid

router = APIRouter(prefix="/sandbox", dependencies=[Depends(requireAdminKey)])


@router.get("/policies")
def getPolicies(identifierType: PolicyIdentifierType, identifierValue: str) -> dict:
    try:
        return {"ok": True, "policies": participantService.getPolicies(identifierType, identifierValue)}
    except Exception as exc:
        raise HTTPException(502, str(exc))


@router.get("/certs")
def fetchParticipantCerts(participantId: str) -> dict:
    try:
        return {"ok": True, "response": certService.fetchCerts(participantId)}
    except Exception as exc:
        raise HTTPException(502, str(exc))


@router.get("/participants")
def listParticipants(role: ParticipantRole, fromdate: str, todate: str) -> dict:
    try:
        return {"ok": True, "response": participantService.listParticipants(role, fromdate, todate)}
    except Exception as exc:
        raise HTTPException(502, str(exc))


class PolicyProduct(BaseModel):
    productid: str
    productname: str


class LinkPolicyRequest(BaseModel):
    confirmSandboxMutation: bool = False
    requestid: str | None = None
    abhanumber: str
    mobilenumber: str
    payerid: str
    memberid: str
    processingid: str
    policies: list[PolicyProduct]


@router.post("/policies/link")
def linkPolicy(req: LinkPolicyRequest) -> dict:
    if not req.confirmSandboxMutation:
        raise HTTPException(400, "set confirmSandboxMutation=true to link sandbox policy data")
    try:
        return {
            "ok": True,
            "response": participantService.linkPolicy(
                abhaNumber=req.abhanumber,
                mobileNumber=req.mobilenumber,
                memberId=req.memberid,
                payerId=req.payerid,
                processingId=req.processingid,
                policies=[policy.model_dump() for policy in req.policies],
                requestId=req.requestid,
            ),
        }
    except Exception as exc:
        raise HTTPException(502, str(exc))


class DelinkPolicyRequest(BaseModel):
    confirmSandboxMutation: bool = False
    requestid: str | None = None
    payerid: str
    memberid: str
    processingid: str
    policies: list[PolicyProduct]


@router.post("/policies/delink")
def delinkPolicy(req: DelinkPolicyRequest) -> dict:
    if not req.confirmSandboxMutation:
        raise HTTPException(400, "set confirmSandboxMutation=true to delink sandbox policy data")
    try:
        return {
            "ok": True,
            "response": participantService.delinkPolicy(
                memberId=req.memberid,
                payerId=req.payerid,
                processingId=req.processingid,
                policies=[policy.model_dump() for policy in req.policies],
                requestId=req.requestid,
            ),
        }
    except Exception as exc:
        raise HTTPException(502, str(exc))


class DummyPayerProcessRequest(BaseModel):
    correlationId: str
    action: DummyPayerAction
    method: DummyPayerMethod


@router.post("/dummy-payer/process")
def processDummyPayerRequest(req: DummyPayerProcessRequest) -> dict:
    try:
        return {"ok": True, "response": dummyPayerService.processRequest(req.correlationId, req.action, req.method)}
    except Exception as exc:
        raise HTTPException(502, str(exc))


class PaymentNoticeInitRequest(BaseModel):
    correlationId: str


@router.post("/dummy-payer/payment-notice")
def initPaymentNotice(req: PaymentNoticeInitRequest) -> dict:
    try:
        return {"ok": True, "response": dummyPayerService.paymentNoticeInit(req.correlationId)}
    except Exception as exc:
        raise HTTPException(502, str(exc))


class StatusCheckRequest(BaseModel):
    recipientCode: str
    targetCorrelationId: str


@router.post("/status-check")
def statusCheck(req: StatusCheckRequest) -> dict:
    try:
        return {"ok": True, "response": hcxApiService.checkStatus(settings.nhcxParticipantCode, req.recipientCode, req.targetCorrelationId)}
    except Exception as exc:
        raise HTTPException(502, str(exc))


class RejectRequest(BaseModel):
    endpoint: OutboundEndpoint          # e.g. COMMUNICATION_REPLY, PAYMENT_NOTICE_ACK
    recipientCode: str
    correlationId: str
    workflowId: str
    entityType: UseCase
    errorCode: str
    errorMessage: str


@router.post("/reject")
def sendRejection(req: RejectRequest) -> dict:
    """§5b — send a ProtocolResponse rejection instead of the normal ack-then-process path."""
    try:
        body = buildRejection(
            senderCode=settings.nhcxParticipantCode, recipientCode=req.recipientCode,
            apiCallId=newUuid(), correlationId=req.correlationId, workflowId=req.workflowId,
            entityType=req.entityType, errorCode=req.errorCode, errorMessage=req.errorMessage,
        )
        return {"ok": True, "response": hcxApiService.sendRejection(req.endpoint.value, body, req.correlationId)}
    except Exception as exc:
        raise HTTPException(502, str(exc))
