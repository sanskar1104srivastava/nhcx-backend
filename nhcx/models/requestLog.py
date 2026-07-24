"""nhcxRequestLog item shape (§7) — one DynamoDB table, partition key apiCallId."""
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from nhcx.constants import LogState


class RequestLogItem(BaseModel):
    apiCallId: str                     # partition key — also the idempotency key for inbound retries
    hospitalId: str
    useCase: str
    direction: str

    correlationId: str                 # GSI partition key — groups every message in a claim cycle
    requestId: str

    workflowId: str
    senderCode: str
    recipientCode: str

    xHcxStatus: str
    protocolStatus: str | None = None

    fhirBundleOut: dict | None = None
    fhirBundleIn: dict | None = None
    jweOut: str | None = None
    jweIn: str | None = None
    largePayloadS3Key: str | None = None   # set instead of the four fields above when they'd blow DynamoDB's 400KB item limit

    state: str = LogState.INITIATED.value
    errorCode: str | None = None
    errorMessage: str | None = None
    retryOf: str | None = None         # apiCallId of the dead predecessor this retry links to

    benAbhaId: str | None = None
    claimNumber: str | None = None
    policyNumber: str | None = None

    createdAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updatedAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
