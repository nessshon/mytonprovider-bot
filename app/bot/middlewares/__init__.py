import logging

from aiogram import Dispatcher, Bot
from sulguk import AiogramSulgukMiddleware

from .db import DbSessionMiddleware
from .i18n import I18nMiddleware
from .throttling import ThrottlingMiddleware

logger = logging.getLogger(__name__)


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

    logger.info("Middlewares registered")


__all__ = ["register"]
