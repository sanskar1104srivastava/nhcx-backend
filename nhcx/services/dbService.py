"""All DynamoDB access for the log table goes through this one service (boto3 itself lives only in AwsService)."""
import json
import logging
from datetime import datetime, timezone

from nhcx.config import settings
from nhcx.constants import LogState
from nhcx.models.requestLog import RequestLogItem
from nhcx.services.awsService import awsService
from nhcx.utils.dynamoDecimalUtil import floatsToDecimal

logger = logging.getLogger(__name__)

# Conservative margin below DynamoDB's real 400KB/item hard limit.
_MAX_ITEM_BYTES = 350_000
_LARGE_FIELDS = ("fhirBundleOut", "fhirBundleIn", "jweOut", "jweIn")


def _offloadLargePayload(itemDict: dict) -> dict:
    """Attachment-bearing bundles (e.g. Communication replies with documents) can blow past
    DynamoDB's item size limit — confirmed for real testing the Communication reply flow.
    Move the bulky fields to S3 and leave a pointer instead of dropping the audit data."""
    size = len(json.dumps(itemDict, default=str))
    if size <= _MAX_ITEM_BYTES:
        return itemDict
    if not settings.largePayloadBucket:
        raise ValueError(
            f"log item for apiCallId={itemDict.get('apiCallId')} is {size} bytes — over DynamoDB's "
            "item limit — and LARGE_PAYLOAD_BUCKET isn't configured to offload it"
        )
    payload = {field: itemDict.pop(field, None) for field in _LARGE_FIELDS}
    key = f"{itemDict['apiCallId']}.json"
    awsService.putS3Object(settings.largePayloadBucket, key, json.dumps(payload, default=str))
    itemDict["largePayloadS3Key"] = key
    logger.info("Offloaded large payload (%d bytes) for apiCallId=%s to s3://%s/%s", size, itemDict.get("apiCallId"), settings.largePayloadBucket, key)
    return itemDict


class DbService:
    def createTableIfNotExists(self) -> None:
        awsService.createTableIfNotExists(
            tableName=settings.dynamoTableName,
            partitionKey="apiCallId",
            globalSecondaryIndexes=[{"indexName": "correlationId-index", "partitionKey": "correlationId"}],
        )

    def insertLog(self, **fields) -> RequestLogItem:
        item = RequestLogItem(**fields)
        try:
            awsService.putItem(
                settings.dynamoTableName,
                floatsToDecimal(_offloadLargePayload(item.model_dump(exclude_none=True))),
                conditionExpression="attribute_not_exists(apiCallId)",  # the "unique constraint" (§7)
            )
        except Exception as exc:
            if awsService.isConditionalCheckFailure(exc):
                logger.info("Duplicate insertLog for apiCallId=%s — returning existing item", item.apiCallId)
                return self.findByApiCallId(item.apiCallId)
            raise
        logger.info("Logged %s %s apiCallId=%s correlationId=%s", item.direction, item.useCase, item.apiCallId, item.correlationId)
        return item

    def findByApiCallId(self, apiCallId: str) -> RequestLogItem | None:
        """Idempotency check for inbound retries — partition-key get, no query needed."""
        data = awsService.getItem(settings.dynamoTableName, {"apiCallId": apiCallId})
        return RequestLogItem(**data) if data else None

    def resolveLargePayload(self, item: RequestLogItem) -> RequestLogItem:
        """Fetches the offloaded bundle/JWE content back from S3 — called on demand (e.g. replay),
        not on every read, since most log views just need state/metadata, not the full payload."""
        if not item.largePayloadS3Key:
            return item
        payload = json.loads(awsService.getS3Object(settings.largePayloadBucket, item.largePayloadS3Key))
        return item.model_copy(update=payload)

    def findByCorrelationId(self, correlationId: str) -> list[RequestLogItem]:
        """Every message in a claim cycle — used to mark the whole cycle dead on a fatal protocol error (§10)."""
        items = awsService.queryIndex(settings.dynamoTableName, "correlationId-index", "correlationId", correlationId)
        return [RequestLogItem(**i) for i in items]

    _LIST_FIELDS = [
        "apiCallId", "hospitalId", "useCase", "direction", "correlationId", "requestId",
        "workflowId", "senderCode", "recipientCode", "xHcxStatus", "protocolStatus",
        "largePayloadS3Key", "state", "errorCode", "errorMessage", "retryOf",
        "benAbhaId", "claimNumber", "policyNumber", "createdAt", "updatedAt",
    ]

    def listRecent(self, limit: int = 50) -> list[RequestLogItem]:
        items = awsService.scanTable(settings.dynamoTableName, projectionFields=self._LIST_FIELDS)
        items.sort(key=lambda i: i.get("createdAt", ""), reverse=True)
        return [RequestLogItem(**i) for i in items[:limit]]

    def updateState(self, item: RequestLogItem, state: LogState, **fields) -> RequestLogItem:
        updated = item.model_copy(update={
            "state": state.value,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            **fields,
        })
        awsService.putItem(settings.dynamoTableName, floatsToDecimal(_offloadLargePayload(updated.model_dump(exclude_none=True))))
        return updated


dbService = DbService()
