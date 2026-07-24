"""Error code taxonomy (§10) — three separate families, parsed differently, never conflated.

1. NHCX-1001..1014   — gateway/protocol errors (ProtocolResponse / /v1/error).
2. PAYR-1001..1020   — payer-side business/transport errors (same transport as above).
3. Adjudication codes (ELIG-/AUTH-/CLAI-/CODE-/DUPL-/MNEC-/NCOV-/PRCE-/TIME-/SURC-/COPY-/WRNG-)
   — arrive *inside* the decrypted ClaimResponse/CoverageEligibilityResponse payload itself,
   never in the protocol-error transport. Human-facing, not something the worker retries.
"""

# Codes with a specific, documented handling rule — the rest of the 1001-1014 / 1001-1020
# ranges exist per NHA's StandardErrorCodes.xlsx but aren't individually actioned here.
NHCX_RECEIVER_UNREACHABLE = "NHCX-1001"   # expect a delayed /v1/error after retries exhaust, not an immediate failure
NHCX_DUPLICATE_CORRELATION_ID = "NHCX-1006"  # our own UUID generation collided — bug on our side, alert immediately
NHCX_INVALID_STATUS = "NHCX-1011"         # the failure mode the §4a preset test is designed to catch

PAYR_DECRYPTION_ERROR = "PAYR-1001"       # treat as: cached recipient cert is stale, force fetch/certs refresh
PAYR_ENCRYPTION_ERROR = "PAYR-1002"       # same handling as above

# error codes that mean our cached recipient cert is stale (§3) — invalidate and retry once
STALE_CERT_ERROR_CODES = {PAYR_DECRYPTION_ERROR, PAYR_ENCRYPTION_ERROR}

# codes that indicate a bug in *our* integration, not a payer/protocol issue — alert engineering
OUR_BUG_ERROR_CODES = {NHCX_DUPLICATE_CORRELATION_ID}

ADJUDICATION_PREFIXES = (
    "ELIG-", "AUTH-", "CLAI-", "CODE-", "DUPL-", "MNEC-",
    "NCOV-", "PRCE-", "TIME-", "SURC-", "COPY-", "WRNG-",
)

# Only the two prefixes the doc gives an explicit meaning for — don't fabricate the rest.
KNOWN_ADJUDICATION_LABELS = {
    "NCOV-": "Not covered under policy",
    "DUPL-": "Duplicate claim detected",
}


def isNhcxProtocolError(code: str) -> bool:
    return code.startswith("NHCX-")


def isPayrError(code: str) -> bool:
    return code.startswith("PAYR-")


def isAdjudicationCode(code: str) -> bool:
    return code.startswith(ADJUDICATION_PREFIXES)


def classify(code: str) -> str:
    """Returns 'protocol_bug' | 'stale_cert' | 'protocol_nhcx' | 'protocol_payr' | 'adjudication' | 'unknown'."""
    if not code:
        return "unknown"
    if code in OUR_BUG_ERROR_CODES:
        return "protocol_bug"
    if code in STALE_CERT_ERROR_CODES:
        return "stale_cert"
    if isNhcxProtocolError(code):
        return "protocol_nhcx"
    if isPayrError(code):
        return "protocol_payr"
    if isAdjudicationCode(code):
        return "adjudication"
    return "unknown"


def adjudicationLabel(code: str) -> str:
    for prefix, label in KNOWN_ADJUDICATION_LABELS.items():
        if code.startswith(prefix):
            return label
    return code  # unmapped prefix — surface the raw code rather than guess its meaning
