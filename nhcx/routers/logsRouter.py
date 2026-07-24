"""Read-only view over nhcx_request_log (§7) for the admin frontend."""
from fastapi import APIRouter, Depends, HTTPException

from nhcx.dependencies import requireAdminKey
from nhcx.services.dbService import dbService

router = APIRouter(prefix="/logs", dependencies=[Depends(requireAdminKey)])


@router.get("")
def listLogs(limit: int = 50) -> list[dict]:
    return [item.model_dump() for item in dbService.listRecent(limit=limit)]


@router.get("/{apiCallId}")
def getLog(apiCallId: str) -> dict:
    """Single entry with its FHIR payload resolved — large bundles live in S3, not the list."""
    item = dbService.findByApiCallId(apiCallId)
    if item is None:
        raise HTTPException(404, "no log entry with that apiCallId")
    return dbService.resolveLargePayload(item).model_dump()
