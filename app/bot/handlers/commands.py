from aiogram import Dispatcher
from aiogram.filters import Command, CommandObject
from aiogram.fsm.state import State
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode, ShowMode

from ..utils import delete_message, is_valid_pubkey
from ...alert.manager import AlertManager
from ...alert.types import AlertTypes, AlertStages
from ...context import Context
from ...database.metrics import build_monthly_report
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
            show_mode=ShowMode.DELETE_AND_SEND,
        )
        await delete_message(message)

    dp.message.register(handler, Command(command))


async def monthly_report_command(
    message: Message,
    command: CommandObject,
    ctx: Context,
    uow: UnitOfWork,
    user_model: UserModel,
) -> None:
    if not command.args:
        return

    pubkey = command.args.strip().lower()
    if not is_valid_pubkey(pubkey):
        return

    subscription = next(
        (
            uta
            for uta in (user_model.subscriptions or [])
            if uta and uta.provider_pubkey == pubkey
        ),
        None,
    )
    if not subscription:
        await delete_message(message)
        return

    provider = await uow.provider.get(pubkey=pubkey)
    if not provider:
        return

    report = await build_monthly_report(uow.session, provider.pubkey)
    alert_manager = AlertManager(ctx)
    await alert_manager.send_alert_message(
        user=user_model,
        alert_type=AlertTypes.MONTHLY_REPORT,
        alert_stage=AlertStages.INFO,
        provider=provider,
        report=report,
    )
