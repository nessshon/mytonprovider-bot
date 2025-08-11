import base64
import hashlib

from ...config import TELEMETRY_URL_SALT


def generate_password_hash(password: str) -> str:
    if not isinstance(password, str):
        raise TypeError("Password must be a string")

    data = TELEMETRY_URL_SALT + password
    data_bytes = data.encode("utf-8")

    hasher = hashlib.sha256(data_bytes)
    hash_bytes = hasher.digest()
    hash_b64 = base64.b64encode(hash_bytes)

    return hash_b64.decode("utf-8")
