from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    nhcxClientId: str = Field("", validation_alias="NHCX_CLIENT_ID")
    nhcxClientSecret: str = Field("", validation_alias="NHCX_CLIENT_SECRET")
    nhcxParticipantCode: str = Field("", validation_alias="NHCX_PARTICIPANT_CODE")

    abdmSessionsUrl: str = Field("https://dev.abdm.gov.in/gateway/v0.5/sessions", validation_alias="ABDM_SESSIONS_URL")
    nhcxGatewayBase: str = Field("https://apisbx.abdm.gov.in/hcx/v1", validation_alias="NHCX_GATEWAY_BASE")
    nhcxParticipantBase: str = Field("https://apisbx.abdm.gov.in/pmjay/sbxhcx/participanthcxservice", validation_alias="NHCX_PARTICIPANT_BASE")
    nhcxDummyPayerBase: str = Field("https://apisbx.abdm.gov.in/pmjay/sbxhcx/dummyhcxpayer", validation_alias="NHCX_DUMMY_PAYER_BASE")
    nhcxBridgeUrl: str = Field("", validation_alias="NHCX_BRIDGE_URL")

    # §4a/4b — NHA docs disagree; presets settle it on the first sandbox call
    nhcxStatusPreset: str = Field("initiated", validation_alias="NHCX_STATUS_PRESET")      # initiated | initiate
    nhcxTimestampPreset: str = Field("iso", validation_alias="NHCX_TIMESTAMP_PRESET")      # iso | epoch_ms

    nhcxPrivateKeySecretName: str = Field("nhcx/private-key", validation_alias="NHCX_PRIVATE_KEY_SECRET_NAME")
    nhcxPrivateKeyPath: str = Field("", validation_alias="NHCX_PRIVATE_KEY_PATH")  # local dev override

    dynamoTableName: str = Field("nhcxRequestLog", validation_alias="DYNAMO_TABLE_NAME")
    dynamoEndpointUrl: str = Field("", validation_alias="DYNAMO_ENDPOINT_URL")  # set for DynamoDB Local, blank for real AWS
    inboundQueueUrl: str = Field("", validation_alias="INBOUND_QUEUE_URL")
    largePayloadBucket: str = Field("", validation_alias="LARGE_PAYLOAD_BUCKET")  # bundles/JWE too big for a DynamoDB item land here
    awsRegion: str = Field("ap-south-1", validation_alias="AWS_REGION")

    nhcxDummyPayerCode: str = Field("1000003538@hcx", validation_alias="NHCX_DUMMY_PAYER_CODE")
    certCacheTtlSeconds: int = Field(86400, validation_alias="CERT_CACHE_TTL_SECONDS")

    # ponytail: offline-dev escape hatch only — sender validation needs a live NHCX call (§11),
    # so pure offline receiver testing needs a way to skip it. Never set true outside local dev.
    skipSenderValidation: bool = Field(False, validation_alias="NHCX_SKIP_SENDER_VALIDATION")

    # §11 — gates the admin/dev-tool routes (test0, sandbox, logs, send). Blank = no gate
    # (local dev default); set this in the deployed env before leaving the stack up unattended.
    adminApiKey: str = Field("", validation_alias="ADMIN_API_KEY")


settings = Settings()
