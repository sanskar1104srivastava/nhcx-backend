"""Run the doc's §8 Test 0 rows against the real NHCX sandbox: auth, our own cert status,
dummy payer cert fetch. Requires .env filled in (NHCX_PARTICIPANT_CODE especially).
Run: python scripts/test0_sandbox_selfcheck.py
"""
import sys

sys.path.insert(0, ".")

from nhcx.config import settings
from nhcx.services.tokenService import tokenService
from nhcx.services.certService import certService


def step(label: str, fn) -> None:
    print(f"--- {label} ---")
    try:
        result = fn()
        print("OK:", result)
    except Exception as exc:
        print("FAILED:", exc)
    print()


if __name__ == "__main__":
    if not settings.nhcxParticipantCode:
        print("NHCX_PARTICIPANT_CODE is not set in .env — fill it in before running this (see §3).")
        sys.exit(1)

    step("Get a token from sessions API", lambda: tokenService.getToken()[:12] + "...")
    step("fetch/certs for our own participant code", lambda: certService.fetchCerts(settings.nhcxParticipantCode))
    step("fetch/certs for the dummy payer", lambda: certService.fetchCerts(settings.nhcxDummyPayerCode))
