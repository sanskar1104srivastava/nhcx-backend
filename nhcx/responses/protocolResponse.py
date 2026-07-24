"""The ProtocolResponse shape (confirmed from NHA's error-handling doc) — used when we choose
to reject an inbound message *after* evaluation (business/clinical grounds), rather than the
default ack-then-process path. Sent unencrypted (protocol-level, not domain payload) to the same
on_request/on_submit endpoint the original message arrived on, in place of a normal JWE payload.
"""
from nhcx.constants import UseCase
from nhcx.utils.timeUtils import formatHcxTimestamp


def buildRejection(
    senderCode: str, recipientCode: str, apiCallId: str, correlationId: str, workflowId: str,
    entityType: UseCase, errorCode: str, errorMessage: str, benAbhaId: str = "",
) -> dict:
    return {
        "type": "ProtocolResponse",
        "x-hcx-sender_code": senderCode,
        "x-hcx-recipient_code": recipientCode,
        "x-hcx-api_call_id": apiCallId,
        "x-hcx-correlation_id": correlationId,
        "x-hcx-workflow_id": workflowId,
        "x-hcx-timestamp": formatHcxTimestamp(),
        "x-hcx-debug_flag": "Error",
        "x-hcx-status": "response.error",
        "x-hcx-redirect_to": "",
        "x-hcx-error_details": {"code": errorCode, "message": errorMessage, "trace": ""},
        "x-hcx-debug_details": {"code": "", "message": "", "trace": ""},
        "x-hcx-entity-type": entityType.value,
        "x-hcx-ben-abha-id": benAbhaId,
    }
