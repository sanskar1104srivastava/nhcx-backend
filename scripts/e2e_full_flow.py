"""
End-to-end NHCX flow test for ABHA 91157848323851.
Links a PMJAY policy, then runs every use case through the full provider→NHCX→payer cycle.

Prerequisites:
  - Local server running (run_local.py)
  - DynamoDB Local on port 8001
  - .env configured with valid sandbox credentials
"""

import json
import sys
import os
import time
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nhcx.config import settings
from nhcx.constants import ParticipantRole
from nhcx.services.tokenService import tokenService
from nhcx.services.participantService import participantService

ABHA_NUMBER = "91157848323851"
PROVIDER_CODE = settings.nhcxParticipantCode  # 1000004604@hcx
DUMMY_PAYER_CODE = settings.nhcxDummyPayerCode  # 1000003538@hcx
LOCAL_BASE = "http://127.0.0.1:8000"
PAYER_BASE = "http://127.0.0.1:8002"
ADMIN_KEY = settings.adminApiKey

PASS = 0
FAIL = 0


def ok(label: str, msg: str = ""):
    global PASS
    PASS += 1
    print(f"  [PASS] {label}" + (f" — {msg}" if msg else ""))


def fail(label: str, msg: str):
    global FAIL
    FAIL += 1
    print(f"  [FAIL] {label} — {msg}")


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def api_call(method: str, url: str, json_body=None, headers=None) -> httpx.Response:
    """Wrapper that prints request/response for debugging."""
    h = headers or {}
    print(f"  → {method.upper()} {url}")
    if json_body:
        print(f"    body keys: {list(json_body.keys()) if isinstance(json_body, dict) else '(non-dict)'}")
    resp = httpx.request(method, url, json=json_body, headers=h, timeout=60)
    print(f"  ← {resp.status_code}")
    if resp.content:
        try:
            rj = resp.json()
            if "error" in rj:
                print(f"    error: {rj['error']}")
            elif "detail" in rj:
                print(f"    detail: {rj['detail']}")
            else:
                print(f"    keys: {list(rj.keys())[:8]}")
        except Exception:
            print(f"    text: {resp.text[:200]}")
    return resp


# ─────────────────────────────────────────────────────────────
# STEP 0: Verify sandbox connectivity
# ─────────────────────────────────────────────────────────────
def test_sandbox_connectivity():
    section("STEP 0: Sandbox Connectivity")
    try:
        token = tokenService.getToken()
        ok("Session token obtained", f"{token[:20]}...")
    except Exception as e:
        fail("Session token", str(e))
        return False

    try:
        my_cert = participantService.listParticipants(ParticipantRole.PROVIDER, "01/01/2024", "31/12/2026")
        ok("Participant list fetched", f"got response")
    except Exception as e:
        fail("Participant list", str(e))

    return True


# ─────────────────────────────────────────────────────────────
# STEP 1: Policy Linking
# ─────────────────────────────────────────────────────────────
def test_policy_linking():
    section("STEP 1: Policy Linking (ABHA -> PMJAY)")
    print(f"  ABHA: {ABHA_NUMBER}")
    print(f"  Provider: {PROVIDER_CODE}")
    print(f"  Dummy Payer: {DUMMY_PAYER_CODE}")

    # Link PMJAY policy
    link_payload = {
        "requestid": str(uuid.uuid4()),
        "abhanumber": ABHA_NUMBER,
        "mobilenumber": "9876543210",
        "payerid": DUMMY_PAYER_CODE,
        "processingid": DUMMY_PAYER_CODE,
        "memberid": f"MEM{ABHA_NUMBER[-6:]}",
        "policies": [
            {
                "productid": "PMJAY",
                "productname": "Ayushman Bharat PMJAY"
            }
        ]
    }

    try:
        resp = participantService.linkPolicy(
            abhaNumber=link_payload["abhanumber"],
            mobileNumber=link_payload["mobilenumber"],
            memberId=link_payload["memberid"],
            payerId=link_payload["payerid"],
            processingId=link_payload["processingid"],
            policies=link_payload["policies"],
            requestId=link_payload["requestid"],
        )
        ok("Policy linked", json.dumps(resp)[:200])
    except Exception as e:
        err_msg = str(e)
        if "already linked" in err_msg.lower() or "200" in err_msg:
            ok("Policy already linked (or linked successfully)", err_msg[:200])
        else:
            fail("Policy linking", err_msg[:200])
            return False

    # Verify: get policies
    try:
        policies = participantService.getPolicies("AbhaNumber", ABHA_NUMBER)
        ok("Linked policies retrieved", json.dumps(policies)[:300])
        return True
    except Exception as e:
        fail("Get policies", str(e)[:200])
        return False


# ─────────────────────────────────────────────────────────────
# STEP 2: Insurance Plan Request
# ─────────────────────────────────────────────────────────────
def test_insurance_plan():
    section("STEP 2: Insurance Plan Request")

    fixture_path = ROOT / "fixtures" / "taskBundleInsurancePlanRequest-dummyPayer.json"
    bundle = json.loads(fixture_path.read_text(encoding="utf-8"))

    # Update bundle with current timestamp
    bundle["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S+05:30")

    payload = {
        "hospitalId": PROVIDER_CODE,
        "useCase": "insuranceplan",
        "endpoint": "/insuranceplan/request",
        "workflowId": "2",
        "recipientCode": DUMMY_PAYER_CODE,
        "fhirBundle": bundle,
    }

    try:
        resp = api_call("post", f"{LOCAL_BASE}/send", json_body=payload,
                        headers={"X-Admin-Key": ADMIN_KEY, "Content-Type": "application/json"})
        if resp.status_code == 200:
            rj = resp.json()
            corr_id = rj.get("correlationId") or rj.get("correlation_id", "")
            ok("Insurance Plan Request sent", f"correlationId={corr_id}")
            return corr_id
        else:
            fail("Insurance Plan Request", f"HTTP {resp.status_code}: {resp.text[:200]}")
            return None
    except Exception as e:
        fail("Insurance Plan Request", str(e)[:200])
        return None


# ─────────────────────────────────────────────────────────────
# STEP 3: Coverage Eligibility Check
# ─────────────────────────────────────────────────────────────
def test_coverage_eligibility():
    section("STEP 3: Coverage Eligibility Check")

    fixture_path = ROOT / "fixtures" / "coverageEligibilityRequestBundle-dummyPayer.json"
    bundle = json.loads(fixture_path.read_text(encoding="utf-8"))

    bundle["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S+05:30")

    # Update Patient ABHA identifier
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Patient":
            for ident in resource.get("identifier", []):
                ident["value"] = "7225-4829-5255"  # Keep Aadhaar
            resource["telecom"][0]["value"] = "+919876543210"

    payload = {
        "hospitalId": PROVIDER_CODE,
        "useCase": "coverageeligibility",
        "endpoint": "/coverageeligibility/check",
        "workflowId": "12",
        "recipientCode": DUMMY_PAYER_CODE,
        "fhirBundle": bundle,
        "beneficiaryId": ABHA_NUMBER,
    }

    try:
        resp = api_call("post", f"{LOCAL_BASE}/send", json_body=payload,
                        headers={"X-Admin-Key": ADMIN_KEY, "Content-Type": "application/json"})
        if resp.status_code == 200:
            rj = resp.json()
            corr_id = rj.get("correlationId") or rj.get("correlation_id", "")
            ok("Coverage Eligibility Check sent", f"correlationId={corr_id}")
            return corr_id
        else:
            fail("Coverage Eligibility Check", f"HTTP {resp.status_code}: {resp.text[:200]}")
            return None
    except Exception as e:
        fail("Coverage Eligibility Check", str(e)[:200])
        return None


# ─────────────────────────────────────────────────────────────
# STEP 4: Preauth Submit + Dummy Payer Action
# ─────────────────────────────────────────────────────────────
def test_preauth(action="Approve"):
    section(f"STEP 4: Preauth Submit → Dummy Payer {action}")

    fixture_path = ROOT / "fixtures" / "claimBundlePreauth-dummyPayer.json"
    bundle = json.loads(fixture_path.read_text(encoding="utf-8"))

    bundle["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S+05:30")

    payload = {
        "hospitalId": PROVIDER_CODE,
        "useCase": "preauth",
        "endpoint": "/preauth/submit",
        "workflowId": "12",
        "recipientCode": DUMMY_PAYER_CODE,
        "fhirBundle": bundle,
        "beneficiaryId": ABHA_NUMBER,
    }

    # Step 4a: Send preauth
    try:
        resp = api_call("post", f"{LOCAL_BASE}/send", json_body=payload,
                        headers={"X-Admin-Key": ADMIN_KEY, "Content-Type": "application/json"})
        if resp.status_code != 200:
            fail("Preauth Submit", f"HTTP {resp.status_code}: {resp.text[:200]}")
            return None
        rj = resp.json()
        corr_id = rj.get("correlationId") or rj.get("correlation_id", "")
        ok("Preauth submitted", f"correlationId={corr_id}")
    except Exception as e:
        fail("Preauth Submit", str(e)[:200])
        return None

    # Step 4b: Tell dummy payer to act
    time.sleep(2)
    try:
        process_resp = api_call("post", f"{LOCAL_BASE}/sandbox/dummy-payer/process",
                                json_body={"correlationId": corr_id, "action": action, "method": "Preauth"},
                                headers={"X-Admin-Key": ADMIN_KEY, "Content-Type": "application/json"})
        if process_resp.status_code == 200:
            ok(f"Dummy Payer {action} triggered", f"method=Preauth")
        else:
            fail(f"Dummy Payer {action}", f"HTTP {process_resp.status_code}: {process_resp.text[:200]}")
    except Exception as e:
        fail(f"Dummy Payer {action}", str(e)[:200])

    return corr_id


# ─────────────────────────────────────────────────────────────
# STEP 5: Claim Submit + Dummy Payer Action
# ─────────────────────────────────────────────────────────────
def test_claim(action="Approve"):
    section(f"STEP 5: Claim Submit → Dummy Payer {action}")

    fixture_path = ROOT / "fixtures" / "claimBundleClaim-dummyPayer.json"
    bundle = json.loads(fixture_path.read_text(encoding="utf-8"))

    bundle["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S+05:30")

    payload = {
        "hospitalId": PROVIDER_CODE,
        "useCase": "claim",
        "endpoint": "/claim/submit",
        "workflowId": "15",
        "recipientCode": DUMMY_PAYER_CODE,
        "fhirBundle": bundle,
        "beneficiaryId": ABHA_NUMBER,
    }

    try:
        resp = api_call("post", f"{LOCAL_BASE}/send", json_body=payload,
                        headers={"X-Admin-Key": ADMIN_KEY, "Content-Type": "application/json"})
        if resp.status_code == 200:
            rj = resp.json()
            corr_id = rj.get("correlationId") or rj.get("correlation_id", "")
            ok("Claim submitted", f"correlationId={corr_id}")

            # Tell dummy payer to act
            time.sleep(2)
            process_resp = api_call("post", f"{LOCAL_BASE}/sandbox/dummy-payer/process",
                                    json_body={"correlationId": corr_id, "action": action, "method": "Claim"},
                                    headers={"X-Admin-Key": ADMIN_KEY, "Content-Type": "application/json"})
            if process_resp.status_code == 200:
                ok(f"Dummy Payer {action} triggered", f"method=Claim")
            else:
                fail(f"Dummy Payer {action}", f"HTTP {process_resp.status_code}: {process_resp.text[:200]}")
            return corr_id
        else:
            fail("Claim Submit", f"HTTP {resp.status_code}: {resp.text[:200]}")
            return None
    except Exception as e:
        fail("Claim Submit", str(e)[:200])
        return None


# ─────────────────────────────────────────────────────────────
# STEP 6: Predetermination Submit
# ─────────────────────────────────────────────────────────────
def test_predetermination():
    section("STEP 6: Predetermination Submit")

    fixture_path = ROOT / "fixtures" / "claimBundlePredetermination-dummyPayer.json"
    bundle = json.loads(fixture_path.read_text(encoding="utf-8"))

    bundle["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S+05:30")

    payload = {
        "hospitalId": PROVIDER_CODE,
        "useCase": "predetermination",
        "endpoint": "/predetermination/submit",
        "workflowId": "12",
        "recipientCode": DUMMY_PAYER_CODE,
        "fhirBundle": bundle,
        "beneficiaryId": ABHA_NUMBER,
    }

    try:
        resp = api_call("post", f"{LOCAL_BASE}/send", json_body=payload,
                        headers={"X-Admin-Key": ADMIN_KEY, "Content-Type": "application/json"})
        if resp.status_code == 200:
            rj = resp.json()
            corr_id = rj.get("correlationId") or rj.get("correlation_id", "")
            ok("Predetermination submitted", f"correlationId={corr_id}")
            return corr_id
        else:
            fail("Predetermination Submit", f"HTTP {resp.status_code}: {resp.text[:200]}")
            return None
    except Exception as e:
        fail("Predetermination Submit", str(e)[:200])
        return None


# ─────────────────────────────────────────────────────────────
# STEP 7: Reprocess / Task Submit
# ─────────────────────────────────────────────────────────────
def test_reprocess():
    section("STEP 7: Reprocess (Task Submit)")

    fixture_path = ROOT / "fixtures" / "taskBundleReprocessRequest.json"
    bundle = json.loads(fixture_path.read_text(encoding="utf-8"))

    bundle["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S+05:30")

    payload = {
        "hospitalId": PROVIDER_CODE,
        "useCase": "task",
        "endpoint": "/task/submit",
        "workflowId": "121",
        "recipientCode": DUMMY_PAYER_CODE,
        "fhirBundle": bundle,
    }

    try:
        resp = api_call("post", f"{LOCAL_BASE}/send", json_body=payload,
                        headers={"X-Admin-Key": ADMIN_KEY, "Content-Type": "application/json"})
        if resp.status_code == 200:
            rj = resp.json()
            corr_id = rj.get("correlationId") or rj.get("correlation_id", "")
            ok("Reprocess submitted", f"correlationId={corr_id}")
            return corr_id
        else:
            fail("Reprocess Submit", f"HTTP {resp.status_code}: {resp.text[:200]}")
            return None
    except Exception as e:
        fail("Reprocess Submit", str(e)[:200])
        return None


# ─────────────────────────────────────────────────────────────
# STEP 8: Search Submit
# ─────────────────────────────────────────────────────────────
def test_search():
    section("STEP 8: Search (Task Submit)")

    fixture_path = ROOT / "fixtures" / "taskBundleSearchRequest.json"
    bundle = json.loads(fixture_path.read_text(encoding="utf-8"))

    bundle["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S+05:30")

    payload = {
        "hospitalId": PROVIDER_CODE,
        "useCase": "search",
        "endpoint": "/search/submit",
        "workflowId": "17",
        "recipientCode": DUMMY_PAYER_CODE,
        "fhirBundle": bundle,
    }

    try:
        resp = api_call("post", f"{LOCAL_BASE}/send", json_body=payload,
                        headers={"X-Admin-Key": ADMIN_KEY, "Content-Type": "application/json"})
        if resp.status_code == 200:
            rj = resp.json()
            corr_id = rj.get("correlationId") or rj.get("correlation_id", "")
            ok("Search submitted", f"correlationId={corr_id}")
            return corr_id
        else:
            fail("Search Submit", f"HTTP {resp.status_code}: {resp.text[:200]}")
            return None
    except Exception as e:
        fail("Search Submit", str(e)[:200])
        return None


# ─────────────────────────────────────────────────────────────
# STEP 9: Status Check
# ─────────────────────────────────────────────────────────────
def test_status_check(correlation_id=None):
    section("STEP 9: Status Check")

    corr_id = correlation_id or str(uuid.uuid4())

    payload = {
        "recipientCode": DUMMY_PAYER_CODE,
        "targetCorrelationId": corr_id,
    }

    try:
        resp = api_call("post", f"{LOCAL_BASE}/sandbox/status-check", json_body=payload,
                        headers={"X-Admin-Key": ADMIN_KEY, "Content-Type": "application/json"})
        if resp.status_code == 200:
            ok("Status check sent", f"correlationId={corr_id}")
        else:
            fail("Status check", f"HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        fail("Status check", str(e)[:200])


# ─────────────────────────────────────────────────────────────
# STEP 10: Communication Flow (initiate from payer side)
# ─────────────────────────────────────────────────────────────
def test_communication_flow():
    section("STEP 10: Communication Flow (Payer → Provider)")

    fixture_path = ROOT / "fixtures" / "taskBundleCommunicationResponse-dummyPayer.json"
    bundle = json.loads(fixture_path.read_text(encoding="utf-8"))

    bundle["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S+05:30")

    # Send communication request from provider to payer (for the payer to then query)
    payload = {
        "hospitalId": PROVIDER_CODE,
        "useCase": "communication",
        "endpoint": "/communication/on_request",
        "workflowId": "24",
        "recipientCode": DUMMY_PAYER_CODE,
        "fhirBundle": bundle,
    }

    try:
        resp = api_call("post", f"{LOCAL_BASE}/send", json_body=payload,
                        headers={"X-Admin-Key": ADMIN_KEY, "Content-Type": "application/json"})
        if resp.status_code == 200:
            rj = resp.json()
            corr_id = rj.get("correlationId") or rj.get("correlation_id", "")
            ok("Communication sent", f"correlationId={corr_id}")
        else:
            fail("Communication", f"HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        fail("Communication", str(e)[:200])


# ─────────────────────────────────────────────────────────────
# STEP 11: Payment Notice Flow
# ─────────────────────────────────────────────────────────────
def test_payment_notice_flow():
    section("STEP 11: Payment Notice Flow")

    # First trigger dummy payer payment notice
    try:
        resp = api_call("post", f"{LOCAL_BASE}/sandbox/dummy-payer/payment-notice",
                        json_body={"correlationId": str(uuid.uuid4())},
                        headers={"X-Admin-Key": ADMIN_KEY, "Content-Type": "application/json"})
        if resp.status_code == 200:
            ok("Payment Notice initiated by dummy payer")
        else:
            fail("Payment Notice init", f"HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        fail("Payment Notice init", str(e)[:200])

    # Send payment notice ack from provider
    fixture_path = ROOT / "fixtures" / "taskBundlePaymentNoticeResponse.json"
    bundle = json.loads(fixture_path.read_text(encoding="utf-8"))
    bundle["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S+05:30")

    payload = {
        "hospitalId": PROVIDER_CODE,
        "useCase": "payment",
        "endpoint": "/paymentnotice/on_request",
        "workflowId": "30",
        "recipientCode": DUMMY_PAYER_CODE,
        "fhirBundle": bundle,
    }

    try:
        resp = api_call("post", f"{LOCAL_BASE}/send", json_body=payload,
                        headers={"X-Admin-Key": ADMIN_KEY, "Content-Type": "application/json"})
        if resp.status_code == 200:
            ok("Payment Notice ack sent")
        else:
            fail("Payment Notice ack", f"HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        fail("Payment Notice ack", str(e)[:200])


# ─────────────────────────────────────────────────────────────
# STEP 12: Check Logs
# ─────────────────────────────────────────────────────────────
def test_logs():
    section("STEP 12: Check Request Logs")
    try:
        resp = api_call("get", f"{LOCAL_BASE}/logs?limit=20",
                        headers={"X-Admin-Key": ADMIN_KEY})
        if resp.status_code == 200:
            rj = resp.json()
            logs = rj.get("logs", rj.get("items", []))
            ok(f"Retrieved {len(logs)} log entries")
            for log in logs[:10]:
                print(f"    {log.get('apiCallId','?')[:12]}... | {log.get('useCase','?')} | {log.get('state','?')} | {log.get('correlationId','?')[:12]}...")
        else:
            fail("Logs", f"HTTP {resp.status_code}")
    except Exception as e:
        fail("Logs", str(e)[:200])


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n{'#'*60}")
    print(f"  NHCX END-TO-END FLOW TEST")
    print(f"  ABHA: {ABHA_NUMBER}")
    print(f"  Provider: {PROVIDER_CODE}")
    print(f"  Dummy Payer: {DUMMY_PAYER_CODE}")
    print(f"{'#'*60}")

    if not test_sandbox_connectivity():
        print("\n[ABORT] Cannot reach sandbox — check .env and network")
        sys.exit(1)

    test_policy_linking()

    # Run all use cases
    test_insurance_plan()
    test_coverage_eligibility()
    preauth_corr = test_preauth("Approve")
    claim_corr = test_claim("Reject")
    test_predetermination()
    test_reprocess()
    test_search()
    test_status_check(preauth_corr)
    test_communication_flow()
    test_payment_notice_flow()
    test_logs()

    # Summary
    print(f"\n{'#'*60}")
    print(f"  RESULTS: {PASS} passed, {FAIL} failed")
    print(f"{'#'*60}")

    sys.exit(1 if FAIL else 0)
