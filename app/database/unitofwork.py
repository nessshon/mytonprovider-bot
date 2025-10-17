from __future__ import annotations

import logging
import typing as t

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .models import (
    ProviderModel,
    ProviderHistoryModel,
    TelemetryModel,
    TelemetryHistoryModel,
    UserModel,
    UserAlertSettingModel,
    UserSubscriptionModel,
    UserTriggeredAlertModel,
    WalletModel,
    WalletHistoryModel,
)
from .repository import BaseRepository as BRepo

logger = logging.getLogger(__name__)


class UnitOfWork:
    session: AsyncSession

    provider: BRepo[ProviderModel]
    provider_history: BRepo[ProviderHistoryModel]
    telemetry: BRepo[TelemetryModel]
    telemetry_history: BRepo[TelemetryHistoryModel]
    user: BRepo[UserModel]
    user_alert_setting: BRepo[UserAlertSettingModel]
    user_subscription: BRepo[UserSubscriptionModel]
    user_triggered_alert: BRepo[UserTriggeredAlertModel]
    wallet: BRepo[WalletModel]
    wallet_history: BRepo[WalletHistoryModel]

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self.session_factory = session_factory

    async def __aenter__(self) -> UnitOfWork:
        self.session = self.session_factory()

        self.provider = BRepo(ProviderModel, self.session)
        self.provider_history = BRepo(ProviderHistoryModel, self.session)
        self.telemetry = BRepo(TelemetryModel, self.session)
        self.telemetry_history = BRepo(TelemetryHistoryModel, self.session)
        self.user = BRepo(UserModel, self.session)
        self.user_alert_setting = BRepo(UserAlertSettingModel, self.session)
        self.user_subscription = BRepo(UserSubscriptionModel, self.session)
        self.user_triggered_alert = BRepo(UserTriggeredAlertModel, self.session)
        self.wallet = BRepo(WalletModel, self.session)
        self.wallet_history = BRepo(WalletHistoryModel, self.session)
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

        if exc:
            logger.error(f"Unit of work error: {exc}")
            raise exc.with_traceback(tb)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
