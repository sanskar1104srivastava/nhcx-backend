"""DynamoDB's boto3 resource layer rejects native float (wants Decimal) — real FHIR bundles
are full of floats (amounts, quantities), so this conversion is required, not optional.

Recursive walker, not a json round-trip: data read back from DynamoDB already contains Decimal
(not float), and json.dumps can't serialize Decimal at all — the round-trip approach crashed
the moment it touched a previously-stored item (confirmed via a real inbound error-handling path).
"""
from decimal import Decimal


def floatsToDecimal(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: floatsToDecimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [floatsToDecimal(v) for v in obj]
    return obj


def decimalsToJsonNumbers(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj == obj.to_integral_value() else float(obj)
    if isinstance(obj, dict):
        return {k: decimalsToJsonNumbers(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [decimalsToJsonNumbers(v) for v in obj]
    return obj
