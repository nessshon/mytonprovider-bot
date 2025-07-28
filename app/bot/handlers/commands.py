from contextlib import suppress

from aiogram import Dispatcher
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode, ShowMode


def register_command(
    dp: Dispatcher,
    command: str,
    state,
) -> None:
    async def handler(message: Message, dialog_manager: DialogManager) -> None:
        await dialog_manager.start(
            state=state,
            mode=StartMode.RESET_STACK,
            show_mode=ShowMode.DELETE_AND_SEND,
        )
        with suppress(TelegramBadRequest):
            await message.delete()

    dp.message.register(handler, Command(command))
