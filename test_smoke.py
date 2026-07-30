"""One runnable self-check for the non-trivial logic (crypto, ack shape, idempotency dedupe).
No AWS creds needed — dbService/awsService is monkeypatched with an in-memory fake.
Run: python test_smoke.py
"""
import re

from jwcrypto import jwk

from nhcx.constants import UseCase, PolicyIdentifierType, ParticipantRole, OutboundEndpoint
from nhcx.requests.outboundRequest import OutboundRequest
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


def testReceiverRouteCoverage():
    from nhcx.routers.receiverRouter import _ENTITY_TYPE_BY_PATH

    for path in (
        "/insuranceplan/on_request",
        "/coverageeligibility/on_check",
        "/preauth/on_submit",
        "/predetermination/on_submit",
        "/claim/on_submit",
        "/communication/request",
        "/paymentnotice/request",
        "/task/on_submit",
        "/search/on_submit",
        "/on_status",
    ):
        assert path in _ENTITY_TYPE_BY_PATH
        assert f"/v1{path}" in _ENTITY_TYPE_BY_PATH
    print("[ok] receiver routes cover documented callback paths with bare and /v1 forms")


def testParticipantServiceSandboxShapes():
    import nhcx.services.participantService as participantModule

    calls = []

    class FakeTokenService:
        def bearerHeaderValue(self):
            return "Bearer fake"

    class FakeResponse:
        status_code = 200
        content = b"{}"

        def json(self):
            return {"ok": True}

        def raise_for_status(self):
            raise AssertionError("raise_for_status should not be called for HTTP 200")

    def fakePost(url, json, headers, timeout):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return FakeResponse()

    originalPost = participantModule.httpx.post
    originalTokenService = participantModule.tokenService
    try:
        participantModule.httpx.post = fakePost
        participantModule.tokenService = FakeTokenService()
        service = participantModule.ParticipantService()
        service.getPolicies(PolicyIdentifierType.MOBILE_NO, "1234567890")
        service.listParticipants(ParticipantRole.PAYER, "10/05/2023", "11/05/2024")
        service.linkPolicy(
            abhaNumber="11223344556677",
            mobileNumber="1234567890",
            memberId="Cust001",
            payerId="1000003308@hcx",
            processingId="1000003308@hcx",
            policies=[{"productid": "Prod01", "productname": "Active Asure"}],
            requestId="req-1",
        )
        service.delinkPolicy(
            memberId="Cust001",
            payerId="1000003308@hcx",
            processingId="1000003308@hcx",
            policies=[{"productid": "Prod01", "productname": "Active Asure"}],
            requestId="req-2",
        )
    finally:
        participantModule.httpx.post = originalPost
        participantModule.tokenService = originalTokenService

    assert calls[0]["json"] == {"identifiertype": "MobileNo", "identifiervalue": "1234567890"}
    assert calls[1]["json"] == {"role": "PAYER", "fromdate": "10/05/2023", "todate": "11/05/2024"}
    assert calls[2]["json"] == {
        "requestid": "req-1",
        "abhanumber": "11223344556677",
        "mobilenumber": "1234567890",
        "memberid": "Cust001",
        "payerid": "1000003308@hcx",
        "processingid": "1000003308@hcx",
        "policies": [{"productid": "Prod01", "productname": "Active Asure"}],
    }
    assert calls[3]["json"] == {
        "requestid": "req-2",
        "memberid": "Cust001",
        "payerid": "1000003308@hcx",
        "processingid": "1000003308@hcx",
        "policies": [{"productid": "Prod01", "productname": "Active Asure"}],
    }
    print("[ok] Participant Service sandbox calls match documented JSON shapes")


def testSandboxMutationGuard():
    from fastapi import HTTPException
    from nhcx.routers.sandboxToolsRouter import LinkPolicyRequest, DelinkPolicyRequest, linkPolicy, delinkPolicy

    policies = [{"productid": "Prod01", "productname": "Active Asure"}]
    linkReq = LinkPolicyRequest(
        abhanumber="11223344556677",
        mobilenumber="1234567890",
        payerid="1000003308@hcx",
        memberid="Cust001",
        processingid="1000003308@hcx",
        policies=policies,
    )
    delinkReq = DelinkPolicyRequest(
        payerid="1000003308@hcx",
        memberid="Cust001",
        processingid="1000003308@hcx",
        policies=policies,
    )

    for func, req in ((linkPolicy, linkReq), (delinkPolicy, delinkReq)):
        try:
            func(req)
        except HTTPException as exc:
            assert exc.status_code == 400
        else:
            raise AssertionError("sandbox policy mutation route did not require confirmation")
    print("[ok] sandbox link/delink routes require explicit mutation confirmation")


def testSendRouteSurfacesOutboundErrors():
    from fastapi import HTTPException
    import nhcx.routers.senderRouter as senderModule

    class FakeHcxApiService:
        def send(self, req):
            raise RuntimeError("NHCX-1002: Sender not registered in NHCX")

    req = OutboundRequest(
        hospitalId="H1",
        useCase=UseCase.PREDETERMINATION,
        endpoint=OutboundEndpoint.PREDETERMINATION,
        workflowId="1",
        recipientCode="1000003538@hcx",
        fhirBundle={"resourceType": "Bundle", "type": "collection", "entry": []},
    )

    originalService = senderModule.hcxApiService
    originalLoggerDisabled = senderModule.logger.disabled
    try:
        senderModule.hcxApiService = FakeHcxApiService()
        senderModule.logger.disabled = True
        try:
            senderModule.send(req)
        except HTTPException as exc:
            assert exc.status_code == 502
            assert "NHCX-1002" in exc.detail
        else:
            raise AssertionError("send route did not surface outbound failure")
    finally:
        senderModule.hcxApiService = originalService
        senderModule.logger.disabled = originalLoggerDisabled
    print("[ok] send route surfaces outbound NHCX errors as 502 details")


def testDummyPayerErrorsIncludeUpstreamBody():
    import nhcx.services.dummyPayerService as dummyModule

    class FakeResponse:
        status_code = 400
        content = b'{"error":{"code":"SBX-005","message":"wrong method"}}'

        def json(self):
            return {"error": {"code": "SBX-005", "message": "wrong method"}}

    try:
        dummyModule._raiseForSandboxError(FakeResponse())
    except Exception as exc:
        assert "SBX-005" in str(exc)
        assert "wrong method" in str(exc)
    else:
        raise AssertionError("dummy payer error body was not surfaced")
    print("[ok] dummy-payer sandbox errors include upstream response body")


def testDummyPayerRetriesTransientQueryPreauth400():
    import nhcx.services.dummyPayerService as dummyModule
    from nhcx.constants import DummyPayerAction, DummyPayerMethod

    calls = []
    sleeps = []

    class FakeTokenService:
        def bearerHeaderValue(self):
            return "Bearer fake"

    class FakeResponse:
        def __init__(self, status_code, body):
            self.status_code = status_code
            self._body = body
            self.content = b"{}"

        def json(self):
            return self._body

    responses = [
        FakeResponse(400, {"error": {"code": "SBX-PENDING", "message": "not ready"}}),
        FakeResponse(200, {"result": {"protocol_status": "request.dispatched"}, "error": None}),
    ]

    def fakePost(url, json, headers, timeout):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return responses.pop(0)

    originalPost = dummyModule.httpx.post
    originalSleep = dummyModule.time.sleep
    originalTokenService = dummyModule.tokenService
    try:
        dummyModule.httpx.post = fakePost
        dummyModule.time.sleep = lambda seconds: sleeps.append(seconds)
        dummyModule.tokenService = FakeTokenService()
        result = dummyModule.DummyPayerService().processRequest(
            "corr-1", DummyPayerAction.QUERY, DummyPayerMethod.PREAUTH
        )
    finally:
        dummyModule.httpx.post = originalPost
        dummyModule.time.sleep = originalSleep
        dummyModule.tokenService = originalTokenService

    assert len(calls) == 2
    assert sleeps == [8]
    assert result["result"]["protocol_status"] == "request.dispatched"
    print("[ok] dummy-payer Query/Preauth retries transient 400 readiness errors")


def testOutboundSendDefaultsCorrelationToApiCallId():
    import nhcx.services.hcxApiService as hcxModule
    from nhcx.models.requestLog import RequestLogItem

    captured = {}

    class FakeDbService:
        def findByCorrelationId(self, correlationId):
            return []

        def insertLog(self, **fields):
            captured["insert"] = fields
            return RequestLogItem(**fields)

        def updateState(self, item, state, **fields):
            captured["state"] = state.value
            captured["update"] = fields
            return item

    class FakeCertService:
        def getCachedPayerCert(self, participantId):
            return {"encryption_cert": "base64-cert"}

    class FakeResponse:
        content = b"{}"

        def json(self):
            return {"result": {"protocol_status": "request.queued"}, "error": None}

        def raise_for_status(self):
            pass

    ids = iter(["primary-api-call", "primary-request-id"])

    def fakeEncrypt(payload, pem, protectedHeader):
        captured["header"] = protectedHeader
        return "encrypted-primary-payload"

    def fakePost(endpoint, jwePayload, includeTypeField=False):
        captured["post"] = {"endpoint": endpoint, "jwePayload": jwePayload, "includeTypeField": includeTypeField}
        return FakeResponse()

    originals = {
        "dbService": hcxModule.dbService,
        "certService": hcxModule.certService,
        "encryptPayload": hcxModule.encryptPayload,
        "wrapCertB64AsPem": hcxModule.wrapCertB64AsPem,
        "_postWithRetry": hcxModule._postWithRetry,
        "newUuid": hcxModule.newUuid,
    }
    try:
        hcxModule.dbService = FakeDbService()
        hcxModule.certService = FakeCertService()
        hcxModule.encryptPayload = fakeEncrypt
        hcxModule.wrapCertB64AsPem = lambda cert: "pem-cert"
        hcxModule._postWithRetry = fakePost
        hcxModule.newUuid = lambda: next(ids)
        hcxModule.hcxApiService.send(
            OutboundRequest(
                hospitalId="H1",
                useCase=UseCase.COVERAGE_ELIGIBILITY,
                endpoint=OutboundEndpoint.COVERAGE_ELIGIBILITY,
                workflowId="12",
                recipientCode="1000003538@hcx",
                fhirBundle={
                    "resourceType": "Bundle",
                    "type": "collection",
                    "entry": [{"fullUrl": "urn:uuid:1", "resource": {"resourceType": "Patient"}}],
                },
            )
        )
    finally:
        for name, value in originals.items():
            setattr(hcxModule, name, value)

    assert captured["header"]["x-hcx-api_call_id"] == "primary-api-call"
    assert captured["header"]["x-hcx-correlation_id"] == "primary-api-call"
    assert captured["insert"]["apiCallId"] == "primary-api-call"
    assert captured["insert"]["correlationId"] == "primary-api-call"
    assert captured["state"] == "acked"
    print("[ok] outbound primary send defaults correlation_id to api_call_id")


def testStatusCheckUsesOfficialTaskPayloadAndOriginalCorrelation():
    import nhcx.services.hcxApiService as hcxModule
    from nhcx.models.requestLog import RequestLogItem

    originalBundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "fullUrl": "urn:uuid:1",
                "resource": {"resourceType": "CoverageEligibilityRequest"},
            }
        ],
    }
    captured = {}

    class FakeDbService:
        def findByCorrelationId(self, correlationId):
            assert correlationId == "cycle-correlation"
            return [
                RequestLogItem(
                    apiCallId="original-api-call",
                    hospitalId="H1",
                    useCase=UseCase.COVERAGE_ELIGIBILITY.value,
                    direction="outbound",
                    correlationId=correlationId,
                    requestId="original-request",
                    workflowId="wf-1",
                    senderCode="1000004604@hcx",
                    recipientCode="1000003538@hcx",
                    xHcxStatus="request.initiated",
                    fhirBundleOut=originalBundle,
                )
            ]

        def resolveLargePayload(self, item):
            return item

        def insertLog(self, **fields):
            captured["insert"] = fields
            return RequestLogItem(**fields)

        def updateState(self, item, state, **fields):
            captured["state"] = state.value
            captured["update"] = fields
            return item

    class FakeCertService:
        def getCachedPayerCert(self, participantId):
            assert participantId == "1000003538@hcx"
            return {"encryption_cert": "base64-cert"}

    class FakeResponse:
        content = b"{}"

        def json(self):
            return {"result": {"protocol_status": "request.queued"}, "error": None}

        def raise_for_status(self):
            pass

    ids = iter(["status-api-call", "status-request-id"])

    def fakeEncrypt(payload, pem, protectedHeader):
        captured["payload"] = payload
        captured["header"] = protectedHeader
        return "encrypted-status-payload"

    def fakePost(endpoint, jwePayload, includeTypeField=False):
        captured["post"] = {"endpoint": endpoint, "jwePayload": jwePayload, "includeTypeField": includeTypeField}
        return FakeResponse()

    originals = {
        "dbService": hcxModule.dbService,
        "certService": hcxModule.certService,
        "encryptPayload": hcxModule.encryptPayload,
        "wrapCertB64AsPem": hcxModule.wrapCertB64AsPem,
        "_postWithRetry": hcxModule._postWithRetry,
        "newUuid": hcxModule.newUuid,
    }
    try:
        hcxModule.dbService = FakeDbService()
        hcxModule.certService = FakeCertService()
        hcxModule.encryptPayload = fakeEncrypt
        hcxModule.wrapCertB64AsPem = lambda cert: "pem-cert"
        hcxModule._postWithRetry = fakePost
        hcxModule.newUuid = lambda: next(ids)
        hcxModule.hcxApiService.checkStatus("H1", "1000003538@hcx", "cycle-correlation")
    finally:
        for name, value in originals.items():
            setattr(hcxModule, name, value)

    statusTask = captured["payload"]["entry"][0]["resource"]
    assert captured["payload"]["resourceType"] == "Bundle"
    assert statusTask["resourceType"] == "Task"
    assert statusTask["status"] == "requested"
    assert statusTask["code"]["coding"][0]["code"] == "status"
    assert statusTask["focus"]["identifier"]["value"] == "cycle-correlation"
    assert statusTask["input"][0]["valueString"] == UseCase.COVERAGE_ELIGIBILITY.value
    assert statusTask["input"][1]["valueString"] == "original-api-call"
    assert captured["header"]["x-hcx-api_call_id"] == "status-api-call"
    assert captured["header"]["x-hcx-correlation_id"] == "original-api-call"
    assert captured["insert"]["apiCallId"] == "status-api-call"
    assert captured["insert"]["correlationId"] == "original-api-call"
    assert captured["post"] == {
        "endpoint": "/status",
        "jwePayload": "encrypted-status-payload",
        "includeTypeField": False,
    }
    print("[ok] status-check uses official Task payload and sandbox status correlation")


if __name__ == "__main__":
    testJweRoundTrip()
    testCertWrap()
    testAckShapeAndTimestamp()
    testHcxTimestampPresets()
    testDbServiceIdempotency()
    testReceiverRouteCoverage()
    testParticipantServiceSandboxShapes()
    testSandboxMutationGuard()
    testSendRouteSurfacesOutboundErrors()
    testDummyPayerErrorsIncludeUpstreamBody()
    testDummyPayerRetriesTransientQueryPreauth400()
    testOutboundSendDefaultsCorrelationToApiCallId()
    testStatusCheckUsesOfficialTaskPayloadAndOriginalCorrelation()
    print("\nALL SMOKE CHECKS PASSED")
