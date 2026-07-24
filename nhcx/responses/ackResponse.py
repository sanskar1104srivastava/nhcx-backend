"""The mandatory inbound-ack body (§5b) — every receiver endpoint returns exactly this shape."""
from pydantic import BaseModel

from nhcx.constants import UseCase
from nhcx.utils.timeUtils import formatAckTimestamp


class AckResult(BaseModel):
    sender_code: str
    recipient_code: str
    entity_type: UseCase
    protocol_status: str = "request.queued"


class AckError(BaseModel):
    code: str = ""
    message: str = ""


class AckResponse(BaseModel):
    timestamp: str
    api_call_id: str
    correlation_id: str
    result: AckResult
    error: AckError = AckError()

    @classmethod
    def build(cls, apiCallId: str, correlationId: str, senderCode: str, recipientCode: str, entityType: UseCase) -> "AckResponse":
        return cls(
            timestamp=formatAckTimestamp(),
            api_call_id=apiCallId,
            correlation_id=correlationId,
            result=AckResult(sender_code=senderCode, recipient_code=recipientCode, entity_type=entityType),
        )
