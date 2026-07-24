"""NHCX cert responses carry base64 (no PEM wrapper) — wrap before handing to jwcrypto."""


def wrapCertB64AsPem(certB64SingleLine: str) -> str:
    if "-----BEGIN" in certB64SingleLine:
        return certB64SingleLine
    lines = [certB64SingleLine[i:i + 64] for i in range(0, len(certB64SingleLine), 64)]
    return "-----BEGIN CERTIFICATE-----\n" + "\n".join(lines) + "\n-----END CERTIFICATE-----\n"
