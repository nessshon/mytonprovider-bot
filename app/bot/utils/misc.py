import base64
import hashlib
from contextlib import suppress

from aiogram.types import Message

from ...config import TELEMETRY_URL_SALT


def generate_passwd_hash(password: str) -> str:
    if not isinstance(password, str):
        raise TypeError("Password must be a string")

    data = TELEMETRY_URL_SALT + password
    data_bytes = data.encode("utf-8")

    hasher = hashlib.sha256(data_bytes)
    hash_bytes = hasher.digest()
    hash_b64 = base64.b64encode(hash_bytes)

    return hash_b64.decode("utf-8")


async def delete_message(message: Message) -> None:
    with suppress(Exception):
        await message.delete()


def is_valid_pubkey(pubkey: str) -> bool:
    if len(pubkey) != 64:
        return False
    try:
        bytes.fromhex(pubkey)
        return True
    except ValueError:
        return False
