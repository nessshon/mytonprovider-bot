from contextlib import suppress

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message
from aiogram_dialog import DialogManager, ShowMode, StartMode

from ..dialogs import states


async def start_command(message: Message, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(
        states.MainMenu.MAIN,
        mode=StartMode.RESET_STACK,
        show_mode=ShowMode.DELETE_AND_SEND,
    )
    with suppress(TelegramBadRequest):
        await message.delete()
