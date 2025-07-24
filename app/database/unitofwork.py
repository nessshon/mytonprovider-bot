from __future__ import annotations

import typing as t

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncSessionTransaction,
    async_sessionmaker,
)

from .models import (
    ProviderModel,
    TelemetryModel,
    TelemetryHistoryModel,
    UserSubscriptionModel,
    UserModel,
    UserAlertSettingModel,
    UserTriggeredAlertModel,
    ProviderTelemetryModel,
)
from .repository import BaseRepository


class UnitOfWork:
    session: AsyncSession
    transaction: AsyncSessionTransaction

    provider: BaseRepository[ProviderModel]
    telemetry: BaseRepository[TelemetryModel]
    telemetry_history: BaseRepository[TelemetryHistoryModel]
    user_subscription: BaseRepository[UserSubscriptionModel]
    user: BaseRepository[UserModel]
    user_alert_setting: BaseRepository[UserAlertSettingModel]
    user_triggered_alert: BaseRepository[UserTriggeredAlertModel]

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self.session_factory = session_factory

    async def __aenter__(self) -> UnitOfWork:
        self.session = self.session_factory()
        self.transaction = await self.session.begin()

        self.provider = BaseRepository(ProviderModel, self.session)
        self.provider_telemetry = BaseRepository(ProviderTelemetryModel, self.session)

        self.telemetry = BaseRepository(TelemetryModel, self.session)
        self.telemetry_history = BaseRepository(TelemetryHistoryModel, self.session)

        self.user = BaseRepository(UserModel, self.session)
        self.user_subscription = BaseRepository(UserSubscriptionModel, self.session)
        self.user_alert_setting = BaseRepository(UserAlertSettingModel, self.session)
        self.user_triggered_alert = BaseRepository(
            UserTriggeredAlertModel, self.session
        )

        return self

    async def __aexit__(
            self,
            exc_type: t.Optional[type[BaseException]],
            exc: t.Optional[BaseException],
            tb: t.Optional[t.Any],
    ) -> None:
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
        await self.session.close()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
