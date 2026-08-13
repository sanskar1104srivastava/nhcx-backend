import logging
import json
import httpx
from fastapi import HTTPException
from jwcrypto import jwk, jwe
from jwcrypto.common import json_encode

from nhcx.config import settings
from nhcx.services.tokenService import tokenService
from nhcx.utils.idUtils import newUuid
from nhcx.utils.timeUtils import formatHcxTimestamp
from nhcx.utils.certPemUtils import wrapCertB64AsPem

logger = logging.getLogger(__name__)


class PayerService:
    def __init__(self):
        # We fetch token dynamically per request to ensure it's fresh
        self.participant_base_url = settings.nhcxParticipantBase
        self.gateway_base_url = settings.nhcxGatewayBase  # e.g. "https://apisbx.abdm.gov.in/hcx/v1"

    def _get_headers(self) -> dict:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "bearer_auth": f"Bearer {tokenService.getToken()}"
        }

    def _fetch_encryption_cert(self, participant_id: str) -> str:
        """Fetches and wraps the encryption certificate for the recipient."""
        logger.info(f"Fetching encryption cert for participant: {participant_id}")
        url = f"{self.participant_base_url}/fetch/certs"
        try:
            response = httpx.post(url, json={"participantid": participant_id}, headers=self._get_headers())
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch cert for {participant_id}: {e}")
            raise HTTPException(status_code=502, detail=f"Failed to fetch cert: {e}")

        encryption_cert_b64 = response.json().get("encryption_cert")
        if not encryption_cert_b64:
            logger.error(f"No encryption certificate registered for participant {participant_id}")
            raise ValueError(f"No encryption certificate registered for participant {participant_id}")

        return wrapCertB64AsPem(encryption_cert_b64)

    def _encrypt_payload(self, plaintext_obj: dict, recipient_public_cert_pem: str, protected_header: dict) -> str:
        """Encrypts the FHIR payload into a JWE string."""
        logger.info("Encrypting payload into JWE string")
        key = jwk.JWK.from_pem(recipient_public_cert_pem.encode())
        complete_header = {**protected_header, "alg": "RSA-OAEP-256", "enc": "A256GCM"}
        token = jwe.JWE(plaintext=json.dumps(plaintext_obj).encode(), protected=json_encode(complete_header))
        token.add_recipient(key)
        return token.serialize(compact=True)

    def _send_to_gateway(self, endpoint_path: str, provider_code: str, fhir_payload: dict,
                         workflow_id: str, hcx_status: str, correlation_id: str = None,
                         is_reply: bool = False) -> dict:
        """Builds headers, encrypts, and sends the request to the NHCX Gateway."""
        api_call_id = newUuid()
        if correlation_id is None:
            correlation_id = api_call_id  # Initiating requests start a new correlation

        sender_code = settings.nhcxParticipantCode

        protected_header = {
            "x-hcx-api_call_id": api_call_id,
            "x-hcx-correlation_id": correlation_id,
            "x-hcx-timestamp": formatHcxTimestamp(),
            "x-hcx-sender_code": sender_code,
            "x-hcx-recipient_code": provider_code,
            "x-hcx-status": hcx_status,
            "x-hcx-workflow_id": workflow_id or "1",
            "x-hcx-ben_abha_id": ""
        }

        logger.info(
            f"Sending to gateway {endpoint_path} for provider {provider_code}. Correlation ID: {correlation_id}")

        cert_pem = self._fetch_encryption_cert(provider_code)
        jwe_payload = self._encrypt_payload(fhir_payload, cert_pem, protected_header)

        body = {"payload": jwe_payload}
        if is_reply:
            body = {"type": "JWEPayload", **body}

        url = f"{self.gateway_base_url}{endpoint_path}"
        logger.info(f"Sending POST request to {url}")

        try:
            response = httpx.post(url, json=body, headers=self._get_headers(), timeout=30)
            logger.info(f"Response Status: {response.status_code}")
            if response.content:
                logger.info(f"Response Body: {response.json()}")

            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=response.json())

            response.raise_for_status()
            return response.json() if response.content else {}
        except httpx.HTTPError as e:
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_json = e.response.json()
                    raise HTTPException(status_code=e.response.status_code, detail=error_json)
                except Exception:
                    pass
            error_msg = f"{e} - body: {e.response.text if hasattr(e, 'response') else ''}"
            logger.error(f"Gateway request failed: {error_msg}")
            raise HTTPException(status_code=502, detail=error_msg)

    # APIs the Payer must CALL to respond
    def respond_insurance_plan(self, fhir_payload: dict, provider_code: str, correlation_id: str,
                               workflow_id: str = "1"):
        return self._send_to_gateway("/insuranceplan/on_request", provider_code, fhir_payload, workflow_id,
                                     "response.complete", correlation_id, is_reply=True)

    def respond_coverage_eligibility(self, fhir_payload: dict, provider_code: str, correlation_id: str,
                                     workflow_id: str = "1"):
        return self._send_to_gateway("/coverageeligibility/on_check", provider_code, fhir_payload, workflow_id,
                                     "response.complete", correlation_id, is_reply=True)

    def respond_preauth(self, fhir_payload: dict, provider_code: str, correlation_id: str, workflow_id: str = "1"):
        return self._send_to_gateway("/preauth/on_submit", provider_code, fhir_payload, workflow_id,
                                     "response.complete", correlation_id, is_reply=True)

    def respond_claim(self, fhir_payload: dict, provider_code: str, correlation_id: str, workflow_id: str = "1"):
        return self._send_to_gateway("/claim/on_submit", provider_code, fhir_payload, workflow_id, "response.complete",
                                     correlation_id, is_reply=True)

    def respond_search(self, fhir_payload: dict, provider_code: str, correlation_id: str, workflow_id: str = "1"):
        return self._send_to_gateway("/search/on_submit", provider_code, fhir_payload, workflow_id, "response.complete",
                                     correlation_id, is_reply=True)

    def respond_task(self, fhir_payload: dict, provider_code: str, correlation_id: str, workflow_id: str = "1"):
        return self._send_to_gateway("/task/on_submit", provider_code, fhir_payload, workflow_id, "response.complete",
                                     correlation_id, is_reply=True)

    def respond_communication(self, fhir_payload: dict, provider_code: str, correlation_id: str,
                              workflow_id: str = "1"):
        return self._send_to_gateway("/communication/on_request", provider_code, fhir_payload, workflow_id,
                                     "response.complete", correlation_id, is_reply=True)

    # APIs the Payer can INITIATE
    def request_communication(self, fhir_payload: dict, provider_code: str, workflow_id: str = "1"):
        return self._send_to_gateway("/communication/request", provider_code, fhir_payload, workflow_id,
                                     "request.initiated", is_reply=False)

    def send_payment_notice(self, fhir_payload: dict, provider_code: str, workflow_id: str = "1"):
        return self._send_to_gateway("/paymentnotice/request", provider_code, fhir_payload, workflow_id,
                                     "request.initiated", is_reply=False)

    def check_status(self, provider_code: str, original_correlation_id: str, workflow_id: str = "1"):
        status_payload = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [{"resource": {"resourceType": "Task", "intent": "order", "status": "requested",
                                    "focus": {"identifier": {"value": original_correlation_id}}}}]
        }
        return self._send_to_gateway("/status", provider_code, status_payload, workflow_id, "request.initiated",
                                     is_reply=False)


payerService = PayerService()
