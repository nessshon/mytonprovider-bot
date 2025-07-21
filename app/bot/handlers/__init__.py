from aiogram import Dispatcher, F
from aiogram.enums import ChatType
from aiogram.filters import ExceptionTypeFilter, CommandStart
from aiogram_dialog.api.exceptions import UnknownIntent, UnknownState

from .commands import start_command
from .common import defaul_message, providers_inline
from .errors import on_unknown_intent, on_unknown_state


def register(dp: Dispatcher) -> None:
    dp.message.register(start_command, CommandStart())
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
