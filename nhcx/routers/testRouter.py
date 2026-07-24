"""Dev-only Test 0 endpoints (§8) — exposed so the admin frontend can drive them.
Gated by requireAdminKey (§11) — no-op until ADMIN_API_KEY is set in the environment.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException

from nhcx.config import settings
from nhcx.dependencies import requireAdminKey
from nhcx.services.tokenService import tokenService
from nhcx.services.certService import certService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/test0", dependencies=[Depends(requireAdminKey)])


@router.get("/token")
def checkToken() -> dict:
    try:
        token = tokenService.getToken()
        return {"ok": True, "tokenPreview": token[:24] + "..."}
    except Exception as exc:
        raise HTTPException(502, str(exc))


@router.get("/certs/self")
def checkOwnCert() -> dict:
    if not settings.nhcxParticipantCode:
        raise HTTPException(400, "NHCX_PARTICIPANT_CODE not set in .env")
    try:
        return {"ok": True, "response": certService.fetchCerts(settings.nhcxParticipantCode)}
    except Exception as exc:
        raise HTTPException(502, str(exc))


@router.get("/certs/payer")
def checkPayerCert() -> dict:
    try:
        return {"ok": True, "response": certService.fetchCerts(settings.nhcxDummyPayerCode)}
    except Exception as exc:
        raise HTTPException(502, str(exc))
