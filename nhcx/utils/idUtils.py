import uuid


def newUuid() -> str:
    return str(uuid.uuid4())


def newUrnUuid() -> str:
    from nhcx.constants import URN_UUID_PREFIX
    return f"{URN_UUID_PREFIX}{uuid.uuid4()}"
