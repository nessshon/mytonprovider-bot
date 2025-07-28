from __future__ import annotations

import asyncio
import typing as t
from datetime import date, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import (
    AsyncSession,
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
    ProviderWalletHistoryModel,
)
from .repository import BaseRepository


class UnitOfWork:
    session: AsyncSession

    provider: BaseRepository[ProviderModel]
    provider_wallet_history: BaseRepository[ProviderWalletHistoryModel]
    provider_telemetry: BaseRepository[ProviderTelemetryModel]
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

        self.provider = BaseRepository(ProviderModel, self.session)
        self.provider_telemetry = BaseRepository(ProviderTelemetryModel, self.session)
        self.provider_wallet_history = BaseRepository(
            ProviderWalletHistoryModel, self.session
        )

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

    async def get_provider_wallet_metrics(
        self,
        pubkey: str,
        today: date,
    ) -> dict:
        latest_stmt = (
            select(
                ProviderWalletHistoryModel.balance,
                ProviderWalletHistoryModel.updated_at,
            )
            .where(ProviderWalletHistoryModel.provider_pubkey == pubkey)
            .order_by(ProviderWalletHistoryModel.date.desc())
            .limit(1)
        )
        result = await self.session.execute(latest_stmt)
        row = result.first()
        balance = row[0] if row else 0
        updated_at = row[1] if row else None

        week_start = today - timedelta(days=7)
        month_start = today - timedelta(days=30)

        def earned_stmt(start: date):
            return select(func.sum(ProviderWalletHistoryModel.earned)).where(
                ProviderWalletHistoryModel.provider_pubkey == pubkey,
                ProviderWalletHistoryModel.date >= start,
                ProviderWalletHistoryModel.date <= today,
            )

        earned_today_stmt = earned_stmt(today)
        earned_week_stmt = earned_stmt(week_start)
        earned_month_stmt = earned_stmt(month_start)
        earned_total_stmt = select(func.sum(ProviderWalletHistoryModel.earned)).where(
            ProviderWalletHistoryModel.provider_pubkey == pubkey
        )

        earned_today, earned_week, earned_month, earned_total = await asyncio.gather(
            *(
                self.session.execute(stmt)
                for stmt in (
                    earned_today_stmt,
                    earned_week_stmt,
                    earned_month_stmt,
                    earned_total_stmt,
                )
            )
        )

        return {
            "balance": balance,
            "updated_at": updated_at,
            "earned_today": earned_today.scalar() or 0,
            "earned_week": earned_week.scalar() or 0,
            "earned_month": earned_month.scalar() or 0,
            "earned_total": earned_total.scalar() or 0,
        }
