"""Enums and constants — no bare strings anywhere else in the codebase."""
from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class Direction(StrEnum):
    OUTBOUND = "outbound"
    INBOUND = "inbound"


class LogState(StrEnum):
    INITIATED = "initiated"
    ACKED = "acked"
    RESPONDED_PARTIAL = "responded_partial"
    RESPONDED_COMPLETE = "responded_complete"
    ERROR = "error"
    DELIVERY_FAILED = "delivery_failed"
    DEAD = "dead"


class UseCase(StrEnum):
    INSURANCE_PLAN = "insuranceplan"
    COVERAGE_ELIGIBILITY = "coverageeligibility"
    PREAUTH = "preauth"
    PREDETERMINATION = "predetermination"
    CLAIM = "claim"
    COMMUNICATION = "communication"
    PAYMENT = "payment"
    TASK = "task"
    SEARCH = "search"
    STATUS = "status"


class HcxStatus(StrEnum):
    REQUEST_INITIATED = "request.initiated"
    REQUEST_INITIATE = "request.initiate"    # §4a rival value
    REQUEST_QUEUED = "request.queued"
    RESPONSE_PARTIAL = "response.partial"
    RESPONSE_COMPLETE = "response.complete"
    RESPONSE_ERROR = "response.error"


class StatusPreset(StrEnum):
    INITIATED = "initiated"
    INITIATE = "initiate"


class TimestampPreset(StrEnum):
    ISO = "iso"
    EPOCH_MS = "epoch_ms"


class Header(StrEnum):
    """JWE protected-header keys (§4c)."""
    ALG = "alg"
    ENC = "enc"
    API_CALL_ID = "x-hcx-api_call_id"
    WORKFLOW_ID = "x-hcx-workflow_id"
    REQUEST_ID = "x-hcx-request_id"
    STATUS = "x-hcx-status"
    TIMESTAMP = "x-hcx-timestamp"
    SENDER_CODE = "x-hcx-sender_code"
    RECIPIENT_CODE = "x-hcx-recipient_code"
    CORRELATION_ID = "x-hcx-correlation_id"
    BEN_ABHA_ID = "x-hcx-ben-abha-id"


ALG_RSA_OAEP_256 = "RSA-OAEP-256"
ENC_A256GCM = "A256GCM"
BEARER_AUTH_HEADER = "bearer_auth"   # NOT Authorization — confirmed across all NHA examples
ACCEPT_HEADER = "Accept"
CONTENT_TYPE_HEADER = "Content-Type"
APPLICATION_JSON = "application/json"
PAYLOAD_KEY = "payload"


class OutboundEndpoint(StrEnum):
    """Gateway paths we call (§5a), relative to {NHCX_GATEWAY_BASE} (which already ends in /hcx/v1)."""
    INSURANCE_PLAN = "/insuranceplan/request"
    COVERAGE_ELIGIBILITY = "/coverageeligibility/check"
    PREAUTH = "/preauth/submit"
    PREDETERMINATION = "/predetermination/submit"
    CLAIM = "/claim/submit"
    COMMUNICATION_REPLY = "/communication/on_request"
    PAYMENT_NOTICE_ACK = "/paymentnotice/on_request"
    REPROCESS = "/task/submit"
    SEARCH = "/search/submit"
    STATUS = "/status"


class ParticipantEndpoint(StrEnum):
    """Plain JSON, no JWE (§6) — relative to NHCX_PARTICIPANT_BASE."""
    FETCH_CERTS = "/fetch/certs"
    PARTICIPANTS_LIST = "/fetch/participants/list"
    PARTICIPANT_UPDATE = "/participant/update"
    GET_POLICIES = "/participant/get/policies"
    LINK_POLICY = "/participant/link/abha/policy"
    DELINK_POLICY = "/participant/delink/abha/policy"


class PolicyIdentifierType(StrEnum):
    ABHA_NUMBER = "AbhaNumber"
    MEMBER_ID = "MemberId"
    MOBILE_NO = "MobileNo"


class ParticipantRole(StrEnum):
    PAYER = "PAYER"
    PROVIDER = "PROVIDER"
    TPA = "TPA"


class DummyPayerEndpoint(StrEnum):
    """Sandbox-only side channel that drives the dummy payer's decision (§9 tests 3-7) —
    relative to NHCX_DUMMY_PAYER_BASE. Not part of the real NHCX protocol."""
    PROCESS_REQUEST = "/process/request"
    PAYMENT_NOTICE_INIT = "/paymentNotice/init"


class DummyPayerAction(StrEnum):
    APPROVE = "Approve"
    REJECT = "Reject"
    QUERY = "Query"


class DummyPayerMethod(StrEnum):
    PREAUTH = "Preauth"
    CLAIM = "Claim"

FHIR_IG_VERSION = "ndhm.in#6.5.0"
BUNDLE_TYPE_COLLECTION = "collection"
URN_UUID_PREFIX = "urn:uuid:"

# Claim.use values sharing the one ClaimBundle shape (§6)
class ClaimUse(StrEnum):
    PREAUTHORIZATION = "preauthorization"
    PREDETERMINATION = "predetermination"
    CLAIM = "claim"


TOKEN_REFRESH_FRACTION = 0.8
ACK_TIMESTAMP_FORMAT = "%d/%m/%Y %H:%M:%S"   # + :mmm appended manually (§5b)
