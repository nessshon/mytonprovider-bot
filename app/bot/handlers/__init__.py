from aiogram import Dispatcher, F
from aiogram.enums import ChatType
from aiogram.filters import ExceptionTypeFilter
from aiogram_dialog.api.exceptions import UnknownIntent, UnknownState

from .commands import register_command
from .common import defaul_message, providers_inline
from .errors import on_unknown_intent, on_unknown_state
from ..dialogs import states


def register(dp: Dispatcher) -> None:
    register_command(dp, "start", states.MainMenu.MAIN)
    register_command(dp, "help", states.HelpMenu.MAIN)
    register_command(dp, "lang", states.LanguageMenu.MAIN)

    dp.message.register(defaul_message)

    dp.inline_query.register(
        providers_inline,
        F.query.endswith("providers"),
        F.chat_type == ChatType.SENDER,
    )

    dp.errors.register(
        on_unknown_intent,
        ExceptionTypeFilter(UnknownIntent),
    )
    dp.errors.register(
        on_unknown_state,
        ExceptionTypeFilter(UnknownState),
    )


__all__ = ["register"]
