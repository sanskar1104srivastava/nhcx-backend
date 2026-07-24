"""What a caller must supply to send anything to NHCX — one shape reused across use cases (§5a)."""
from pydantic import BaseModel

from nhcx.constants import UseCase, OutboundEndpoint


class OutboundRequest(BaseModel):
    hospitalId: str
    useCase: UseCase
    endpoint: OutboundEndpoint
    workflowId: str
    recipientCode: str
    fhirBundle: dict
    correlationId: str | None = None   # fresh UUID if None; reuse only for a live claim cycle (§4c)
    benAbhaId: str | None = None
    claimNumber: str | None = None
    policyNumber: str | None = None
