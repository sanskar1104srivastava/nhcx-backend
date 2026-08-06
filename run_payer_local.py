"""Single entrypoint for local dev for the Payer API — wires the same pieces API Gateway + Lambda + DynamoDB + SQS
would in AWS, runs them as one local process, and prints a clear pass/fail preflight so config
or connectivity problems show up immediately instead of as a cryptic 500 on the first request.

For a fully offline run (no real AWS account needed), start DynamoDB Local first:
    docker run -d -p 8001:8000 amazon/dynamodb-local
    export AWS_ACCESS_KEY_ID=local AWS_SECRET_ACCESS_KEY=local   # boto3 needs *some* creds, even fake ones
    (set DYNAMO_ENDPOINT_URL=http://localhost:8001 in .env — already the default there)

Run: python run_payer_local.py
"""
import sys

from nhcx.config import settings


def check(label: str, fn) -> bool:
    try:
        result = fn()
        print(f"[ OK ] {label}: {result}")
        return True
    except Exception as exc:
        print(f"[FAIL] {label}: {exc}")
        return False


def preflight() -> bool:
    print("=== NHCX Payer bridge — local preflight ===")
    ok = True

    ok &= check("Config: NHCX_PARTICIPANT_CODE set", lambda: settings.nhcxParticipantCode or (_ for _ in ()).throw(ValueError("blank — fill in .env")))

    from nhcx.services.tokenService import tokenService
    ok &= check("Auth: sessions API token", lambda: tokenService.getToken()[:16] + "...")

    from nhcx.services.dbService import dbService
    ok &= check(
        "DynamoDB: table reachable" + (f" (local endpoint {settings.dynamoEndpointUrl})" if settings.dynamoEndpointUrl else " (real AWS)"),
        lambda: dbService.createTableIfNotExists() or "ok",
    )

    if settings.inboundQueueUrl:
        from nhcx.services.awsService import awsService
        ok &= check("SQS: queue reachable", lambda: awsService.sendQueueMessage(settings.inboundQueueUrl, '{"preflight":true}') or "ok")
    else:
        print("[ SKIP ] SQS: INBOUND_QUEUE_URL not set — receiver will process inbound messages inline")

    print("=== preflight complete ===\n")
    return ok


if __name__ == "__main__":
    passed = preflight()
    if not passed:
        print("One or more checks failed — fix the above before relying on live sandbox calls.")
        print("Starting the server anyway so you can still exercise routes that don't need the failing dependency.\n")

    import uvicorn
    # Using port 8001 to avoid conflict with the provider running on 8000
    uvicorn.run("nhcx.payer_main:app", host="0.0.0.0", port=8002, reload=True)
