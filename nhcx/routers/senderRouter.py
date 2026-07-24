"""Thin HTTP wrapper over hcxApiService (§5a) — one route, any use case."""
import logging

from fastapi import APIRouter, Depends

from nhcx.dependencies import requireAdminKey
from nhcx.requests.outboundRequest import OutboundRequest
from nhcx.services.hcxApiService import hcxApiService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/send", dependencies=[Depends(requireAdminKey)])


@router.post("")
def send(req: OutboundRequest) -> dict:
    logger.info("Send request hospitalId=%s useCase=%s endpoint=%s", req.hospitalId, req.useCase, req.endpoint)
    return hcxApiService.send(req)
