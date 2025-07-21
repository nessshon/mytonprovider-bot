import typing as t
from datetime import datetime

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from sqlalchemy.orm import selectinload

from ...config import TIMEZONE
from ...context import Context
from ...database.models import UserModel, AlertSettingModel
from ...database.unitofwork import UnitOfWork
from ...scheduler.user_alerts.types import UserAlertTypes


class DbSessionMiddleware(BaseMiddleware):

    async def __call__(
        self,
        handler: t.Callable[[TelegramObject, t.Dict[str, t.Any]], t.Awaitable[t.Any]],
        event: TelegramObject,
        data: t.Dict[str, t.Any],
    ) -> t.Optional[t.Any]:
        user: t.Optional[User] = data.get("event_from_user")
        ctx: t.Optional[Context] = data.get("ctx")

        if not ctx:
            raise RuntimeError("Context is not available in middleware data")

        uow = UnitOfWork(ctx.db.session_factory)

        async with uow:
            if user and not user.is_bot:
                existing = await uow.user.get(
                    user_id=user.id,
                    options=[
                        selectinload(UserModel.subscriptions),
                        selectinload(UserModel.alert_settings),
                    ],
                )
                if existing is None:
                    user_model = UserModel(
                        user_id=user.id,
                        language_code=user.language_code,
                        full_name=user.full_name,
                        username=user.username,
                        created_at=datetime.now(TIMEZONE),
                        alert_settings=AlertSettingModel(
                            user_id=user.id,
                            enabled=True,
                            types=[alert for alert in UserAlertTypes],
                        ),
                    )
                    user_model = await uow.user.create(user_model)
                else:
                    existing.full_name = user.full_name
                    existing.username = user.username
                    user_model = existing
                    await uow.session.flush()

                data["user_model"] = user_model

            data["uow"] = uow
            return await handler(event, data)
