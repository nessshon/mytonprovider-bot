from contextlib import suppress

from aiogram.types import Message


async def delete_message(message: Message) -> None:
    with suppress(Exception):
        await message.delete()
