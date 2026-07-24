"""Loads our RSA private key — local file in dev, Secrets Manager in prod (§3)."""
from functools import lru_cache

from nhcx.config import settings
from nhcx.services.awsService import awsService


@lru_cache(maxsize=1)
def getPrivateKeyPem() -> bytes:
    if settings.nhcxPrivateKeyPath:
        with open(settings.nhcxPrivateKeyPath, "rb") as f:
            return f.read()
    return awsService.getSecretString(settings.nhcxPrivateKeySecretName).encode()
