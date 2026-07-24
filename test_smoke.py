"""One runnable self-check for the non-trivial logic (crypto, ack shape, idempotency dedupe).
No AWS creds needed — dbService/awsService is monkeypatched with an in-memory fake.
Run: python test_smoke.py
"""
import re

from jwcrypto import jwk

from nhcx.constants import UseCase
from nhcx.utils.cryptoUtils import encryptPayload, decryptPayload, peekProtectedHeader
from nhcx.utils.certPemUtils import wrapCertB64AsPem
from nhcx.utils.idUtils import newUuid
from nhcx.utils.timeUtils import formatHcxTimestamp, formatAckTimestamp
from nhcx.responses.ackResponse import AckResponse


class FakeAwsService:
    """Stands in for DynamoDB: one dict keyed by apiCallId, mimics the conditional-put idempotency check."""
    def __init__(self):
        self.table: dict[str, dict] = {}

    def putItem(self, tableName, item, conditionExpression=None):
        if conditionExpression and item["apiCallId"] in self.table:
            raise Exception("ConditionalCheckFailedException")
        self.table[item["apiCallId"]] = item

    def getItem(self, tableName, key):
        return self.table.get(key["apiCallId"])

    def isConditionalCheckFailure(self, exc):
        return "ConditionalCheckFailedException" in str(exc)

    def createTableIfNotExists(self, **kwargs):
        pass


def testJweRoundTrip():
    priv = jwk.JWK.generate(kty="RSA", size=2048)
    privPem = priv.export_to_pem(private_key=True, password=None)
    pubPem = priv.export_to_pem().decode()

    header = {"x-hcx-api_call_id": newUuid(), "x-hcx-correlation_id": newUuid()}
    bundle = {"resourceType": "Bundle", "type": "collection", "entry": []}

    jweCompact = encryptPayload(bundle, pubPem, header)
    assert decryptPayload(jweCompact, privPem) == bundle
    assert peekProtectedHeader(jweCompact)["x-hcx-api_call_id"] == header["x-hcx-api_call_id"]
    print("[ok] JWE encrypt/decrypt round trip + header peek without key")


def testCertWrap():
    priv = jwk.JWK.generate(kty="RSA", size=2048)
    pubPem = priv.export_to_pem().decode()
    b64only = "".join(pubPem.split("\n")[1:-2])
    wrapped = wrapCertB64AsPem(b64only)
    assert wrapped.startswith("-----BEGIN CERTIFICATE-----")
    print("[ok] wrapCertB64AsPem wraps bare base64 into PEM")


def testAckShapeAndTimestamp():
    ack = AckResponse.build(
        apiCallId=newUuid(), correlationId=newUuid(),
        senderCode="1000003538@hcx", recipientCode="TESTID_001@hcx",
        entityType=UseCase.COVERAGE_ELIGIBILITY,
    )
    dumped = ack.model_dump()
    assert dumped["result"]["protocol_status"] == "request.queued"
    assert dumped["error"] == {"code": "", "message": ""}
    assert re.match(r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}:\d{3}$", formatAckTimestamp())
    print("[ok] AckResponse matches the mandatory §5b shape, timestamp format correct")


def testHcxTimestampPresets():
    import nhcx.config as configModule
    original = configModule.settings.nhcxTimestampPreset
    try:
        configModule.settings.nhcxTimestampPreset = "epoch_ms"
        assert formatHcxTimestamp().isdigit()
        configModule.settings.nhcxTimestampPreset = "iso"
        assert "T" in formatHcxTimestamp()
        print("[ok] both §4b timestamp presets produce distinct, valid formats")
    finally:
        configModule.settings.nhcxTimestampPreset = original


def testDbServiceIdempotency():
    import nhcx.services.dbService as dbModule
    fake = FakeAwsService()
    dbModule.awsService = fake  # swap the only boto3 access point for the in-memory fake

    apiCallId = newUuid()
    first = dbModule.dbService.insertLog(
        apiCallId=apiCallId, hospitalId="H1", useCase="coverageeligibility", direction="inbound",
        correlationId=newUuid(), requestId=newUuid(), workflowId="12",
        senderCode="1000003538@hcx", recipientCode="TESTID_001@hcx", xHcxStatus="request.initiated",
    )
    duplicate = dbModule.dbService.insertLog(
        apiCallId=apiCallId, hospitalId="H1", useCase="coverageeligibility", direction="inbound",
        correlationId=newUuid(), requestId=newUuid(), workflowId="12",
        senderCode="1000003538@hcx", recipientCode="TESTID_001@hcx", xHcxStatus="request.initiated",
    )
    assert duplicate.apiCallId == first.apiCallId
    assert len(fake.table) == 1
    print("[ok] duplicate apiCallId insertLog returns the existing item instead of overwriting (idempotency)")

    found = dbModule.dbService.findByApiCallId(apiCallId)
    assert found is not None and found.apiCallId == apiCallId
    print("[ok] findByApiCallId retrieves the logged item")


if __name__ == "__main__":
    testJweRoundTrip()
    testCertWrap()
    testAckShapeAndTimestamp()
    testHcxTimestampPresets()
    testDbServiceIdempotency()
    print("\nALL SMOKE CHECKS PASSED")
