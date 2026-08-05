import logging
from typing import Optional
from fastapi import APIRouter

from nhcx.services.payerService import payerService
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payer", tags=["Payer"])

class PayerRequest(BaseModel):
    fhir_payload: dict
    provider_code: str
    workflow_id: str = "1"
    correlation_id: Optional[str] = None
    original_correlation_id: Optional[str] = None

@router.post("/insuranceplan/on_request")
def respond_insurance_plan(req: PayerRequest) -> dict:
    logger.info(f"Handling POST /payer/insuranceplan/on_request for provider {req.provider_code}")
    return payerService.respond_insurance_plan(req.fhir_payload, req.provider_code, req.correlation_id, req.workflow_id)

@router.post("/coverageeligibility/on_check")
def respond_coverage_eligibility(req: PayerRequest) -> dict:
    logger.info(f"Handling POST /payer/coverageeligibility/on_check for provider {req.provider_code}")
    return payerService.respond_coverage_eligibility(req.fhir_payload, req.provider_code, req.correlation_id, req.workflow_id)

@router.post("/preauth/on_submit")
def respond_preauth(req: PayerRequest) -> dict:
    logger.info(f"Handling POST /payer/preauth/on_submit for provider {req.provider_code}")
    return payerService.respond_preauth(req.fhir_payload, req.provider_code, req.correlation_id, req.workflow_id)

@router.post("/claim/on_submit")
def respond_claim(req: PayerRequest) -> dict:
    logger.info(f"Handling POST /payer/claim/on_submit for provider {req.provider_code}")
    return payerService.respond_claim(req.fhir_payload, req.provider_code, req.correlation_id, req.workflow_id)

@router.post("/search/on_submit")
def respond_search(req: PayerRequest) -> dict:
    logger.info(f"Handling POST /payer/search/on_submit for provider {req.provider_code}")
    return payerService.respond_search(req.fhir_payload, req.provider_code, req.correlation_id, req.workflow_id)

@router.post("/task/on_submit")
def respond_task(req: PayerRequest) -> dict:
    logger.info(f"Handling POST /payer/task/on_submit for provider {req.provider_code}")
    return payerService.respond_task(req.fhir_payload, req.provider_code, req.correlation_id, req.workflow_id)

@router.post("/communication/on_request")
def respond_communication(req: PayerRequest) -> dict:
    logger.info(f"Handling POST /payer/communication/on_request for provider {req.provider_code}")
    return payerService.respond_communication(req.fhir_payload, req.provider_code, req.correlation_id, req.workflow_id)

@router.post("/communication/request")
def request_communication(req: PayerRequest) -> dict:
    logger.info(f"Handling POST /payer/communication/request for provider {req.provider_code}")
    return payerService.request_communication(req.fhir_payload, req.provider_code, req.workflow_id)

@router.post("/paymentnotice/request")
def send_payment_notice(req: PayerRequest) -> dict:
    logger.info(f"Handling POST /payer/paymentnotice/request for provider {req.provider_code}")
    return payerService.send_payment_notice(req.fhir_payload, req.provider_code, req.workflow_id)

@router.post("/status")
def check_status(req: PayerRequest) -> dict:
    logger.info(f"Handling POST /payer/status for provider {req.provider_code}")
    return payerService.check_status(req.provider_code, req.original_correlation_id, req.workflow_id)
