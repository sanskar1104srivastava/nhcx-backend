"""Two separate timestamp formats — do not conflate them (§4b vs §5b)."""
from datetime import datetime, timezone

from nhcx.config import settings
from nhcx.constants import TimestampPreset, ACK_TIMESTAMP_FORMAT


def formatHcxTimestamp(now: datetime | None = None) -> str:
    """Protected-header x-hcx-timestamp (§4b) — driven by NHCX_TIMESTAMP_PRESET."""
    now = now or datetime.now(timezone.utc)
    if settings.nhcxTimestampPreset == TimestampPreset.EPOCH_MS.value:
        return str(int(now.timestamp() * 1000))
    # ISO 8601 with offset, e.g. 2023-11-06T13:22:06+0530
    return now.strftime("%Y-%m-%dT%H:%M:%S%z") or now.isoformat()


def formatAckTimestamp(now: datetime | None = None) -> str:
    """Inbound-ack body timestamp (§5b): DD/MM/YYYY hh:mm:ss:sss."""
    now = now or datetime.now(timezone.utc)
    millis = f"{now.microsecond // 1000:03d}"
    return f"{now.strftime(ACK_TIMESTAMP_FORMAT)}:{millis}"
