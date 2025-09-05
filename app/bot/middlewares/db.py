import typing as t
from datetime import datetime

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from ...config import (
    TIMEZONE,
    SUPPORTED_LOCALES,
    DEFAULT_LOCALE,
)
from ...context import Context
from ...database.models import (
    UserModel,
    UserAlertSettingModel,
)
from ...database.unitofwork import UnitOfWork
from ...utils.alerts.types import AlertTypes


class DbSessionMiddleware(BaseMiddleware):

    async def __call__(
        self,
        handler: t.Callable[[TelegramObject, t.Dict[str, t.Any]], t.Awaitable[t.Any]],
        event: TelegramObject,
        data: t.Dict[str, t.Any],
    ) -> t.Optional[t.Any]:
        user: t.Optional[User] = data.get("event_from_user")
        ctx: t.Optional[Context] = data.get("ctx")
        uow = UnitOfWork(ctx.db.session_factory)

        async with uow:
            user_model: t.Optional[UserModel] = None
            has_subscriptions = False

            if user and not user.is_bot:
                existing = await uow.user.get(user_id=user.id)

                if existing is None:
                    user_language_code = (
                        user.language_code
                        if user.language_code in SUPPORTED_LOCALES
                        else DEFAULT_LOCALE
                    )
                    user_model = UserModel(
                        user_id=user.id,
                        language_code=user_language_code,
                        full_name=user.full_name,
                        username=user.username,
                        created_at=datetime.now(TIMEZONE),
                        alert_settings=UserAlertSettingModel(
                            user_id=user.id,
                            enabled=False,
                            types=[alert for alert in AlertTypes],
                        ),
                    )
                    user_model = await uow.user.create(user_model)
                else:
                    existing_language_code = (
                        existing.language_code
                        if existing.language_code in SUPPORTED_LOCALES
                        else DEFAULT_LOCALE
                    )
                    existing.full_name = user.full_name
                    existing.username = user.username
                    existing.language_code = existing_language_code
                    user_model = existing
                    await uow.session.flush()

                has_subscriptions = await uow.user_subscription.exists(
                    user_id=user_model.id
                )

            data["user_model"] = user_model
            data["has_subscriptions"] = has_subscriptions
            data["uow"] = uow

            return await handler(event, data)
