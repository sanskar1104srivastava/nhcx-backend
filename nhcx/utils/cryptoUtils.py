"""RSA-OAEP-256 + A256GCM JWE, RFC 7516 compact serialization (§4d)."""
import json

from jwcrypto import jwk, jwe
from jwcrypto.common import json_encode

from nhcx.constants import ALG_RSA_OAEP_256, ENC_A256GCM


def encryptPayload(plaintextObj: dict, recipientPublicCertPem: str, protectedHeader: dict) -> str:
    key = jwk.JWK.from_pem(recipientPublicCertPem.encode())
    token = jwe.JWE(
        plaintext=json.dumps(plaintextObj).encode(),
        protected=json_encode({**protectedHeader, "alg": ALG_RSA_OAEP_256, "enc": ENC_A256GCM}),
    )
    token.add_recipient(key)
    return token.serialize(compact=True)


def decryptPayload(jweCompact: str, ourPrivateKeyPem: bytes) -> dict:
    key = jwk.JWK.from_pem(ourPrivateKeyPem)
    token = jwe.JWE()
    token.deserialize(jweCompact, key=key)
    return json.loads(token.payload)


def peekProtectedHeader(jweCompact: str) -> dict:
    """JWE protected header is unencrypted (first compact-serialization segment) —
    read api_call_id/correlation_id for the immediate ack without decrypting the body."""
    token = jwe.JWE()
    token.deserialize(jweCompact)
    return token.jose_header
