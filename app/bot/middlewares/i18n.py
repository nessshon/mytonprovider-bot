from __future__ import annotations

import typing as t
from collections.abc import Awaitable, Callable

from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import TelegramObject, User

from ...config import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
)
from ...context import Context
from ...utils.i18n import Localizer


class I18nMiddleware(BaseMiddleware):

    async def __call__(
            self,
            handler: Callable[[TelegramObject, t.Dict[str, t.Any]], Awaitable[t.Any]],
            event: TelegramObject,
            data: t.Dict[str, t.Any],
    ) -> t.Any:
        user: t.Optional[User] = data.get("event_from_user")
        ctx: Context = data.get("ctx")

        if user is not None and not user.is_bot:
            user_model = data.get("user_model")

            if (
                    user_model
                    and getattr(user_model, "language_code", None) in SUPPORTED_LOCALES
            ):
                language_code = user_model.language_code
            elif user.language_code in SUPPORTED_LOCALES:
                language_code = user.language_code
            else:
                language_code = DEFAULT_LOCALE
            locale_data = ctx.i18n.locales_data.get(language_code)

            if locale_data is None:
                raise ValueError(
                    f"Localization for language '{language_code}' not found in locales_data."
                )

            data["localizer"] = Localizer(
                jinja_env=ctx.i18n.jinja_env,
                locale_data=locale_data,
            )

        return await handler(event, data)
