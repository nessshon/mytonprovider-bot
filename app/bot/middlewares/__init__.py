from aiogram import Dispatcher, Bot
from sulguk import AiogramSulgukMiddleware

from .db import DbSessionMiddleware
from .i18n import I18nMiddleware
from .throttling import ThrottlingMiddleware


def register(dp: Dispatcher, bot: Bot) -> None:
    bot.session.middleware(AiogramSulgukMiddleware())

    throttling_middleware = ThrottlingMiddleware()
    db_middleware = DbSessionMiddleware()
    i18n_middleware = I18nMiddleware()

    dp.update.middleware(db_middleware)
    dp.update.middleware(i18n_middleware)
    dp.update.middleware(throttling_middleware)

    dp.error.middleware(db_middleware)
    dp.error.middleware(i18n_middleware)
    dp.error.middleware(throttling_middleware)


__all__ = ["register"]
