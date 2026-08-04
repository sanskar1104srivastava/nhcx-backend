import os
import sys
import json
import httpx
import uuid
import datetime
from jwcrypto import jwk, jwe
from jwcrypto.common import json_encode

def newUuid() -> str:
    return str(uuid.uuid4())

def formatHcxTimestamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec='milliseconds')

class NHCXPayerClient:
    def __init__(self, sender_code: str, token: str, 
                 participant_base_url: str = "https://apisbx.abdm.gov.in/pmjay/sbxhcx/participanthcxservice",
                 gateway_base_url: str = "https://apisbx.abdm.gov.in/hcx/v1"):
        self.sender_code = sender_code
        self.token = token
        self.participant_base_url = participant_base_url
        self.gateway_base_url = gateway_base_url
        self._headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "bearer_auth": f"Bearer {self.token}"
        }

    def _fetch_encryption_cert(self, participant_id: str) -> str:
        """Fetches and wraps the encryption certificate for the recipient."""
        url = f"{self.participant_base_url}/fetch/certs"
        response = httpx.post(url, json={"participantid": participant_id}, headers=self._headers)
        response.raise_for_status()
        
        encryption_cert_b64 = response.json().get("encryption_cert")
        if not encryption_cert_b64:
            raise ValueError(f"No encryption certificate registered for participant {participant_id}")
            
        from nhcx.utils.certPemUtils import wrapCertB64AsPem
        return wrapCertB64AsPem(encryption_cert_b64)

    def _encrypt_payload(self, plaintext_obj: dict, recipient_public_cert_pem: str, protected_header: dict) -> str:
        """Encrypts the FHIR payload into a JWE string."""
        key = jwk.JWK.from_pem(recipient_public_cert_pem.encode())
        complete_header = {**protected_header, "alg": "RSA-OAEP-256", "enc": "A256GCM"}
        token = jwe.JWE(plaintext=json.dumps(plaintext_obj).encode(), protected=json_encode(complete_header))
        token.add_recipient(key)
        return token.serialize(compact=True)

    def _send_to_gateway(self, endpoint_path: str, provider_code: str, fhir_payload: dict, 
                         workflow_id: str, hcx_status: str, correlation_id: str = None, 
                         is_reply: bool = False):
        """Builds headers, encrypts, and sends the request to the NHCX Gateway."""
        api_call_id = newUuid()
        if correlation_id is None:
            correlation_id = api_call_id # Initiating requests start a new correlation

        protected_header = {
            "x-hcx-api_call_id": api_call_id,
            "x-hcx-correlation_id": correlation_id,
            "x-hcx-timestamp": formatHcxTimestamp(),
            "x-hcx-sender_code": self.sender_code,
            "x-hcx-recipient_code": provider_code,
            "x-hcx-status": hcx_status,
            "x-hcx-workflow_id": workflow_id or "1",
            "x-hcx-ben_abha_id": ""
        }

        print(f"[*] Fetching cert for recipient: {provider_code}")
        cert_pem = self._fetch_encryption_cert(provider_code)
        
        print(f"[*] Encrypting payload...")
        jwe_payload = self._encrypt_payload(fhir_payload, cert_pem, protected_header)
        
        # Payer Responses (on_request/on_submit) require the "type": "JWEPayload" field 
        # in the outer envelope, otherwise NHCX gateway drops it.
        body = {"payload": jwe_payload}
        if is_reply:
            body = {"type": "JWEPayload", **body}
            
        url = f"{self.gateway_base_url}{endpoint_path}"
        print(f"[*] Sending POST request to {url}")
        response = httpx.post(url, json=body, headers=self._headers, timeout=30)
        
        print(f"[*] Response Status: {response.status_code}")
        if response.content:
            print(f"[*] Response Body: {response.json()}")
        response.raise_for_status()
        return response.json() if response.content else {}

    # ==============================================================================
    # APIs the Payer must CALL to respond (is_reply = True, status = response.complete)
    # ==============================================================================
    def respond_insurance_plan(self, fhir_payload: dict, provider_code: str, correlation_id: str, workflow_id: str = "1"):
        return self._send_to_gateway("/insuranceplan/on_request", provider_code, fhir_payload, workflow_id, "response.complete", correlation_id, is_reply=True)

    def respond_coverage_eligibility(self, fhir_payload: dict, provider_code: str, correlation_id: str, workflow_id: str = "1"):
        return self._send_to_gateway("/coverageeligibility/on_check", provider_code, fhir_payload, workflow_id, "response.complete", correlation_id, is_reply=True)

    def respond_preauth(self, fhir_payload: dict, provider_code: str, correlation_id: str, workflow_id: str = "1"):
        return self._send_to_gateway("/preauth/on_submit", provider_code, fhir_payload, workflow_id, "response.complete", correlation_id, is_reply=True)

    def respond_claim(self, fhir_payload: dict, provider_code: str, correlation_id: str, workflow_id: str = "1"):
        return self._send_to_gateway("/claim/on_submit", provider_code, fhir_payload, workflow_id, "response.complete", correlation_id, is_reply=True)

    def respond_search(self, fhir_payload: dict, provider_code: str, correlation_id: str, workflow_id: str = "1"):
        return self._send_to_gateway("/search/on_submit", provider_code, fhir_payload, workflow_id, "response.complete", correlation_id, is_reply=True)

    def respond_task(self, fhir_payload: dict, provider_code: str, correlation_id: str, workflow_id: str = "1"):
        return self._send_to_gateway("/task/on_submit", provider_code, fhir_payload, workflow_id, "response.complete", correlation_id, is_reply=True)

    def respond_communication(self, fhir_payload: dict, provider_code: str, correlation_id: str, workflow_id: str = "1"):
        return self._send_to_gateway("/communication/on_request", provider_code, fhir_payload, workflow_id, "response.complete", correlation_id, is_reply=True)


    # ==============================================================================
    # APIs the Payer can INITIATE (is_reply = False, status = request.initiate)
    # ==============================================================================
    def request_communication(self, fhir_payload: dict, provider_code: str, workflow_id: str = "1"):
        """Payer asks provider for more documents."""
        return self._send_to_gateway("/communication/request", provider_code, fhir_payload, workflow_id, "request.initiated", is_reply=False)

    def send_payment_notice(self, fhir_payload: dict, provider_code: str, workflow_id: str = "1"):
        """Payer sends a payment notice / reconciliation to provider."""
        return self._send_to_gateway("/paymentnotice/request", provider_code, fhir_payload, workflow_id, "request.initiated", is_reply=False)

    def check_status(self, provider_code: str, original_correlation_id: str, original_usecase: str, workflow_id: str = "1"):
        """Payer checks status of a request."""
        # Status payload requires a specific Task bundle
        status_payload = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [{"resource": {"resourceType": "Task", "intent": "order", "status": "requested", "focus": {"identifier": {"value": original_correlation_id}}}}]
        }
        return self._send_to_gateway("/status", provider_code, status_payload, workflow_id, "request.initiated", is_reply=False)


if __name__ == "__main__":
    import os
    import sys
    from dotenv import load_dotenv

    # Add the backend root to the python path so we can import the nhcx module
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from nhcx.services.tokenService import tokenService
    from nhcx.config import settings

    load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env')))
    
    # We must use our OWN backend's participant code as the sender because we don't have
    # the OAuth client_secret for the Dummy Payer. We can send messages to the Dummy Payer 
    # to simulate a provider, or send messages to ourselves to simulate a payer!
    NHCX_TOKEN = tokenService.getToken()
    MY_SENDER_CODE = settings.nhcxParticipantCode 
    TARGET_PROVIDER = "1000004604@hcx" # Sending to ourselves for testing, or put another provider code here

    client = NHCXPayerClient(sender_code=MY_SENDER_CODE, token=NHCX_TOKEN)

    print("===================================================================")
    print("Testing NHCX Payer Client API")
    print("===================================================================\n")

    # ===================================================================
    # Payer-Initiated APIs
    # ===================================================================
    dummy_bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [{"resource": {"resourceType": "Basic", "status": "active"}}]
    }

    try:
        print("--> 1. Initiating Payment Notice (/paymentnotice/request)")
        client.send_payment_notice(dummy_bundle, TARGET_PROVIDER)
        print("Success!\n")
    except Exception as e:
        print(f"Failed: {e}\n")

    try:
        print("--> 2. Requesting Communication (/communication/request)")
        client.request_communication(dummy_bundle, TARGET_PROVIDER)
        print("Success!\n")
    except Exception as e:
        print(f"Failed: {e}\n")

    try:
        print("--> 3. Checking Status (/status)")
        # Usually takes the api_call_id of the request you want to check
        client.check_status(TARGET_PROVIDER, original_correlation_id=newUuid(), original_usecase="preauth")
        print("Success!\n")
    except Exception as e:
        print(f"Failed: {e}\n")


    # ===================================================================
    # Payer Response APIs
    # ===================================================================
    print("\n-------------------------------------------------------------------")
    print("Payer Response APIs")
    print("For each API below, provide a valid Correlation ID from a Provider's request.")
    print("If you don't have one for a specific API, just press Enter to skip it.")
    print("-------------------------------------------------------------------\n")

    preauth_corr_id = input("Enter Correlation ID for PREAUTH response (or press Enter to skip): ").strip()
    if preauth_corr_id:
        try:
            print("--> 4. Responding to Preauth (/preauth/on_submit)")
            client.respond_preauth(dummy_bundle, TARGET_PROVIDER, preauth_corr_id)
            print("Success!\n")
        except Exception as e:
            print(f"Failed: {e}\n")

    claim_corr_id = input("Enter Correlation ID for CLAIM response (or press Enter to skip): ").strip()
    if claim_corr_id:
        try:
            print("--> 5. Responding to Claim (/claim/on_submit)")
            client.respond_claim(dummy_bundle, TARGET_PROVIDER, claim_corr_id)
            print("Success!\n")
        except Exception as e:
            print(f"Failed: {e}\n")

    cov_corr_id = input("Enter Correlation ID for COVERAGE ELIGIBILITY response (or press Enter to skip): ").strip()
    if cov_corr_id:
        try:
            print("--> 6. Responding to Coverage Eligibility (/coverageeligibility/on_check)")
            client.respond_coverage_eligibility(dummy_bundle, TARGET_PROVIDER, cov_corr_id)
            print("Success!\n")
        except Exception as e:
            print(f"Failed: {e}\n")

    ins_corr_id = input("Enter Correlation ID for INSURANCE PLAN response (or press Enter to skip): ").strip()
    if ins_corr_id:
        try:
            print("--> 7. Responding to Insurance Plan (/insuranceplan/on_request)")
            client.respond_insurance_plan(dummy_bundle, TARGET_PROVIDER, ins_corr_id)
            print("Success!\n")
        except Exception as e:
            print(f"Failed: {e}\n")

    search_corr_id = input("Enter Correlation ID for SEARCH response (or press Enter to skip): ").strip()
    if search_corr_id:
        try:
            print("--> 8. Responding to Search (/search/on_submit)")
            client.respond_search(dummy_bundle, TARGET_PROVIDER, search_corr_id)
            print("Success!\n")
        except Exception as e:
            print(f"Failed: {e}\n")

    task_corr_id = input("Enter Correlation ID for TASK response (or press Enter to skip): ").strip()
    if task_corr_id:
        try:
            print("--> 9. Responding to Task (/task/on_submit)")
            client.respond_task(dummy_bundle, TARGET_PROVIDER, task_corr_id)
            print("Success!\n")
        except Exception as e:
            print(f"Failed: {e}\n")

