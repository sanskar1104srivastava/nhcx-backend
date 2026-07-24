"""Single point of access to AWS/Boto3 (per project guidelines) — no other module imports boto3 directly."""
import logging
from functools import lru_cache

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from nhcx.config import settings

logger = logging.getLogger(__name__)


class AwsService:
    def __init__(self) -> None:
        self._secretsClient = boto3.client("secretsmanager", region_name=settings.awsRegion)
        dynamoKwargs = {"region_name": settings.awsRegion}
        if settings.dynamoEndpointUrl:  # DynamoDB Local for offline dev — real AWS otherwise
            dynamoKwargs["endpoint_url"] = settings.dynamoEndpointUrl
            # boto3's default ~60s connect/retry timeout makes a wrong/dead local endpoint hang
            # for a very long time instead of failing fast — only apply the short timeout locally.
            dynamoKwargs["config"] = Config(connect_timeout=3, retries={"max_attempts": 1})
        self._dynamoResource = boto3.resource("dynamodb", **dynamoKwargs)
        self._dynamoClient = boto3.client("dynamodb", **dynamoKwargs)
        self._sqsClient = boto3.client("sqs", region_name=settings.awsRegion)
        self._s3Client = boto3.client("s3", region_name=settings.awsRegion)

    @lru_cache(maxsize=8)
    def getSecretString(self, secretName: str) -> str:
        logger.info("Fetching secret %s from Secrets Manager", secretName)
        return self._secretsClient.get_secret_value(SecretId=secretName)["SecretString"]

    def putItem(self, tableName: str, item: dict, conditionExpression: str | None = None) -> None:
        kwargs = {"Item": item}
        if conditionExpression:
            kwargs["ConditionExpression"] = conditionExpression
        self._dynamoResource.Table(tableName).put_item(**kwargs)

    def getItem(self, tableName: str, key: dict) -> dict | None:
        return self._dynamoResource.Table(tableName).get_item(Key=key).get("Item")

    def queryIndex(self, tableName: str, indexName: str, keyName: str, keyValue: str) -> list[dict]:
        from boto3.dynamodb.conditions import Key
        return self._dynamoResource.Table(tableName).query(
            IndexName=indexName, KeyConditionExpression=Key(keyName).eq(keyValue),
        ).get("Items", [])

    def scanTable(self, tableName: str, projectionFields: list[str] | None = None) -> list[dict]:
        # Paginated, metadata-only scan. A single un-paginated scan stops at DynamoDB's 1MB
        # page, and with full FHIR bundles stored per item that silently dropped newer rows
        # from the admin log view. Projecting only the light columns keeps pages small.
        # ponytail: still a full scan — switch to a createdAt GSI if the table grows large.
        table = self._dynamoResource.Table(tableName)
        kwargs = {}
        if projectionFields:
            # alias every field — some (state, timestamp-ish names) collide with reserved words
            names = {f"#f{i}": f for i, f in enumerate(projectionFields)}
            kwargs = {"ProjectionExpression": ", ".join(names), "ExpressionAttributeNames": names}
        items: list[dict] = []
        while True:
            response = table.scan(**kwargs)
            items.extend(response.get("Items", []))
            lastKey = response.get("LastEvaluatedKey")
            if not lastKey:
                return items
            kwargs["ExclusiveStartKey"] = lastKey

    def sendQueueMessage(self, queueUrl: str, bodyJson: str) -> None:
        self._sqsClient.send_message(QueueUrl=queueUrl, MessageBody=bodyJson)

    def putS3Object(self, bucket: str, key: str, bodyJson: str) -> None:
        self._s3Client.put_object(Bucket=bucket, Key=key, Body=bodyJson.encode(), ContentType="application/json")

    def getS3Object(self, bucket: str, key: str) -> str:
        return self._s3Client.get_object(Bucket=bucket, Key=key)["Body"].read().decode()

    def isConditionalCheckFailure(self, exc: Exception) -> bool:
        return isinstance(exc, ClientError) and exc.response["Error"]["Code"] == "ConditionalCheckFailedException"

    def createTableIfNotExists(self, tableName: str, partitionKey: str, globalSecondaryIndexes: list[dict] | None = None) -> None:
        try:
            self._dynamoClient.describe_table(TableName=tableName)
            return
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "ResourceNotFoundException":
                raise

        attributeDefinitions = [{"AttributeName": partitionKey, "AttributeType": "S"}]
        gsiSpec = []
        for gsi in globalSecondaryIndexes or []:
            attributeDefinitions.append({"AttributeName": gsi["partitionKey"], "AttributeType": "S"})
            gsiSpec.append({
                "IndexName": gsi["indexName"],
                "KeySchema": [{"AttributeName": gsi["partitionKey"], "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            })

        logger.info("Creating DynamoDB table %s", tableName)
        kwargs = dict(
            TableName=tableName,
            AttributeDefinitions=attributeDefinitions,
            KeySchema=[{"AttributeName": partitionKey, "KeyType": "HASH"}],
            BillingMode="PAY_PER_REQUEST",
        )
        if gsiSpec:
            kwargs["GlobalSecondaryIndexes"] = gsiSpec
        self._dynamoClient.create_table(**kwargs)
        self._dynamoClient.get_waiter("table_exists").wait(TableName=tableName)


awsService = AwsService()
