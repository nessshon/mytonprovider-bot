from aiogram import Dispatcher
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.state import State
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode, ShowMode

from ..dialogs import states
from ..utils import delete_message, is_valid_pubkey
from ...database.models import UserModel
from ...database.unitofwork import UnitOfWork


def register_command(
    dp: Dispatcher,
    command: str,
    state: State,
) -> None:
    async def handler(message: Message, dialog_manager: DialogManager) -> None:
        await dialog_manager.start(
            state=state,
            mode=StartMode.RESET_STACK,
            show_mode=ShowMode.SEND,
        )
        await delete_message(message)

    dp.message.register(handler, Command(command))


def register_start_deeplink(dp: Dispatcher) -> None:

    async def handler(
        message: Message,
        command: CommandObject,
        dialog_manager: DialogManager,
    ) -> None:
        uow: UnitOfWork = dialog_manager.middleware_data["uow"]
        user: UserModel = dialog_manager.middleware_data["user_model"]
        pubkey = (command.args or "").strip().lower()

        if not is_valid_pubkey(pubkey):
            target = {"state": states.MainMenu.INVALID_INPUT}
        elif not await uow.provider.exists(pubkey=pubkey):
            target = {"state": states.MainMenu.NOT_FOUND}
        else:
            is_subscribed = any(
                s.provider_pubkey == pubkey for s in (user.subscriptions or [])
            )
            state = (
                states.ProviderMenu.MAIN
                if is_subscribed
                else states.ProviderMenu.ENTER_PASSWORD
            )
            target = {"state": state, "data": {"provider_pubkey": pubkey}}

        await dialog_manager.start(
            mode=StartMode.RESET_STACK,
            show_mode=ShowMode.SEND,
            **target,
        )
        await delete_message(message)

    dp.message.register(handler, CommandStart(deep_link=True))
