from __future__ import annotations

import typing as t

from sqlalchemy.ext.asyncio.session import (
    AsyncSession,
    AsyncSessionTransaction,
    async_sessionmaker,
)

from .repositories import (
    ProviderRepository,
    TelemetryRepository,
    TelemetryHistoryRepository,
    UserRepository,
    SubscriptionRepository,
    AlertSettingRepository,
    TrigeredAlertRepository,
)


class UnitOfWork:
    session: AsyncSession
    transaction: AsyncSessionTransaction

    provider: ProviderRepository
    telemetry: TelemetryRepository
    telemetry_history: TelemetryHistoryRepository
    subscription: SubscriptionRepository
    user: UserRepository
    alert_setting: AlertSettingRepository
    triggered_alert: TrigeredAlertRepository

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self.session_factory: async_sessionmaker = session_factory

    async def __aenter__(self) -> UnitOfWork:
        self.session = self.session_factory()
        self.transaction = await self.session.begin()

        self.provider = ProviderRepository(self.session)
        self.telemetry = TelemetryRepository(self.session)
        self.telemetry_history = TelemetryHistoryRepository(self.session)
        self.subscription = SubscriptionRepository(self.session)
        self.user = UserRepository(self.session)
        self.alert_setting = AlertSettingRepository(self.session)
        self.triggered_alert = TrigeredAlertRepository(self.session)

        return self

    async def __aexit__(
        self,
        exc_type: t.Optional[t.Type[BaseException]],
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
