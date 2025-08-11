import logging

from aiogram import F, Dispatcher
from aiogram.enums import ChatType
from aiogram.filters import ExceptionTypeFilter
from aiogram_dialog.api.exceptions import (
    UnknownIntent,
    UnknownState,
)
from aiogram_dialog.context.intent_filter import IntentFilter

from .commands import register_command
from .common import (
    default_message,
    hide_callback_query,
    my_chat_memeber,
    providers_inline,
    enter_password_message,
)
from .errors import (
    on_unknown_intent,
    on_unknown_state,
)
from ..dialogs import states

logger = logging.getLogger(__name__)


def register(dp: Dispatcher) -> None:
    register_command(dp, "start", states.MainMenu.MAIN)
    register_command(dp, "help", states.HelpMenu.MAIN)
    register_command(dp, "lang", states.LanguageMenu.MAIN)

    dp.errors.register(
        on_unknown_intent,
        ExceptionTypeFilter(UnknownIntent),
    )
    dp.errors.register(
        on_unknown_state,
        ExceptionTypeFilter(UnknownState),
    )
    dp.inline_query.register(
        providers_inline,
        F.query.endswith("providers"),
        F.chat_type == ChatType.SENDER,
    )

    dp.message.register(
        enter_password_message,
        IntentFilter(states.ProviderMenu),
    )
    dp.message.register(default_message)
    dp.my_chat_member.register(my_chat_memeber)
    dp.callback_query.register(hide_callback_query, F.data == "hide")

    logger.info("Handlers registered")


__all__ = ["register"]
