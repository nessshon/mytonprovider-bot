from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.fsm.state import State
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode, ShowMode

from ..utils import delete_message


def register_command(
    dp: Dispatcher,
    command: str,
    state: State,
) -> None:
    async def handler(message: Message, dialog_manager: DialogManager) -> None:
        await dialog_manager.start(
            state=state,
            mode=StartMode.RESET_STACK,
            show_mode=ShowMode.DELETE_AND_SEND,
        )
        await delete_message(message)

    dp.message.register(handler, Command(command))
