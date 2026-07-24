"""SQS-triggered Lambda — processes inbound NHCX messages queued by the receiver (§5b)."""
import json
import logging

from nhcx.constants import UseCase
from nhcx.services.inboundProcessor import processInboundMessage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def handler(event: dict, context) -> None:
    for record in event["Records"]:
        body = json.loads(record["body"])
        logger.info("Processing queued inbound message apiCallId lookup pending, entityType=%s", body["entityType"])
        processInboundMessage(body["rawBody"], UseCase(body["entityType"]), body["hospitalId"])
