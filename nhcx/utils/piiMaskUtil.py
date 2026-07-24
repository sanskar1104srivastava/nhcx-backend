"""Mask ABHA numbers and mobile numbers before they hit application/CloudWatch logs (§11).
The unmasked value still lives in the DB record (nhcx_request_log) — that's allowed, DB access
is controlled; log aggregators typically have broader read access, so logs get the redacted form.
"""
import re

_MOBILE_RE = re.compile(r"(?<!\d)(?:\+?91[-\s]?)?[6-9]\d{9}(?!\d)")
_ABHA_NUMBER_RE = re.compile(r"\b\d{2}-?\d{4}-?\d{4}-?\d{4}\b")


def maskPii(text: str) -> str:
    if not text:
        return text
    text = _MOBILE_RE.sub("[MOBILE_REDACTED]", text)
    text = _ABHA_NUMBER_RE.sub("[ABHA_REDACTED]", text)
    return text
