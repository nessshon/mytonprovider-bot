from __future__ import annotations

import asyncio
import logging
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
    UserSubscriptionModel,
    UserModel,
    UserAlertSettingModel,
    UserTriggeredAlertModel,
    ProviderTelemetryModel,
    ProviderWalletHistoryModel,
    ProviderTrafficHistoryModel,
    ProviderStorageHistoryModel,
)
from .repository import BaseRepository as BRepo

logger = logging.getLogger(__name__)


class UnitOfWork:
    session: AsyncSession

    provider: BRepo[ProviderModel]
    provider_wallet_history: BRepo[ProviderWalletHistoryModel]
    provider_traffic_history: BRepo[ProviderTrafficHistoryModel]
    provider_storage_history: BRepo[ProviderStorageHistoryModel]
    provider_telemetry: BRepo[ProviderTelemetryModel]
    telemetry: BRepo[TelemetryModel]
    user_subscription: BRepo[UserSubscriptionModel]
    user: BRepo[UserModel]
    user_alert_setting: BRepo[UserAlertSettingModel]
    user_triggered_alert: BRepo[UserTriggeredAlertModel]

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self.session_factory = session_factory

    async def __aenter__(self) -> UnitOfWork:
        self.session = self.session_factory()

        self.provider = BRepo(ProviderModel, self.session)
        self.provider_telemetry = BRepo(ProviderTelemetryModel, self.session)
        self.provider_wallet_history = BRepo(ProviderWalletHistoryModel, self.session)
        self.provider_traffic_history = BRepo(ProviderTrafficHistoryModel, self.session)
        self.provider_storage_history = BRepo(ProviderStorageHistoryModel, self.session)

        self.telemetry = BRepo(TelemetryModel, self.session)

        self.user = BRepo(UserModel, self.session)
        self.user_subscription = BRepo(UserSubscriptionModel, self.session)
        self.user_alert_setting = BRepo(UserAlertSettingModel, self.session)
        self.user_triggered_alert = BRepo(UserTriggeredAlertModel, self.session)

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

    async def get_provider_traffic_metrics(
        self,
        pubkey: str,
        today: date,
    ) -> dict:
        latest_stmt = (
            select(
                ProviderTrafficHistoryModel.updated_at,
                ProviderTrafficHistoryModel.last_bytes_recv,
                ProviderTrafficHistoryModel.last_bytes_sent,
            )
            .where(ProviderTrafficHistoryModel.provider_pubkey == pubkey)
            .order_by(ProviderTrafficHistoryModel.date.desc())
            .limit(1)
        )
        latest_res = await self.session.execute(latest_stmt)
        latest = latest_res.first()
        updated_at = latest[0] if latest else None
        last_bytes_recv = latest[1] if latest else None
        last_bytes_sent = latest[2] if latest else None

        week_start = today - timedelta(days=7)
        month_start = today - timedelta(days=30)

        def sum_stmt(start: date | None):
            stmt = select(
                func.sum(ProviderTrafficHistoryModel.traffic_in),
                func.sum(ProviderTrafficHistoryModel.traffic_out),
            ).where(ProviderTrafficHistoryModel.provider_pubkey == pubkey)
            if start is not None:
                stmt = stmt.where(
                    ProviderTrafficHistoryModel.date >= start,
                    ProviderTrafficHistoryModel.date <= today,
                )
            return stmt

        stmt_today = sum_stmt(today)
        stmt_week = sum_stmt(week_start)
        stmt_month = sum_stmt(month_start)
        stmt_total = sum_stmt(None)

        res_today, res_week, res_month, res_total = await asyncio.gather(
            *(
                self.session.execute(s)
                for s in (stmt_today, stmt_week, stmt_month, stmt_total)
            )
        )

        def parse_two_sums(exec_result) -> tuple[int, int]:
            row = exec_result.first()
            if not row:
                return 0, 0
            s_in = row[0] or 0
            s_out = row[1] or 0
            return int(s_in), int(s_out)

        today_in, today_out = parse_two_sums(res_today)
        week_in, week_out = parse_two_sums(res_week)
        month_in, month_out = parse_two_sums(res_month)
        total_in, total_out = parse_two_sums(res_total)

        return {
            "updated_at": updated_at,
            "last_bytes_recv": last_bytes_recv,
            "last_bytes_sent": last_bytes_sent,
            "traffic_today_in": today_in,
            "traffic_today_out": today_out,
            "traffic_today_total": today_in + today_out,
            "traffic_week_in": week_in,
            "traffic_week_out": week_out,
            "traffic_week_total": week_in + week_out,
            "traffic_month_in": month_in,
            "traffic_month_out": month_out,
            "traffic_month_total": month_in + month_out,
            "traffic_total_in": total_in,
            "traffic_total_out": total_out,
            "traffic_total": total_in + total_out,
        }

    async def get_provider_storage_metrics(
        self,
        pubkey: str,
        today: date,
    ) -> dict:
        latest_stmt = (
            select(
                ProviderStorageHistoryModel.updated_at,
                ProviderStorageHistoryModel.total_provider_space,
                ProviderStorageHistoryModel.used_provider_space,
            )
            .where(ProviderStorageHistoryModel.provider_pubkey == pubkey)
            .order_by(ProviderStorageHistoryModel.date.desc())
            .limit(1)
        )
        latest_res = await self.session.execute(latest_stmt)
        latest = latest_res.first()

        updated_at = latest[0] if latest else None
        total_provider_space = (
            float(latest[1]) if latest and latest[1] is not None else None
        )
        used_provider_space = (
            float(latest[2]) if latest and latest[2] is not None else None
        )

        week_start = today - timedelta(days=7)
        month_start = today - timedelta(days=30)

        def sum_stmt(start: date | None):
            stmt = select(func.sum(ProviderStorageHistoryModel.used_daily_space)).where(
                ProviderStorageHistoryModel.provider_pubkey == pubkey
            )
            if start is not None:
                stmt = stmt.where(
                    ProviderStorageHistoryModel.date >= start,
                    ProviderStorageHistoryModel.date <= today,
                )
            return stmt

        stmt_today = sum_stmt(today)
        stmt_week = sum_stmt(week_start)
        stmt_month = sum_stmt(month_start)
        stmt_total = sum_stmt(None)

        res_today, res_week, res_month, res_total = await asyncio.gather(
            *(
                self.session.execute(s)
                for s in (stmt_today, stmt_week, stmt_month, stmt_total)
            )
        )

        def parse_sum(exec_result) -> float:
            row = exec_result.first()
            return float(row[0] or 0.0) if row else 0.0

        used_today = parse_sum(res_today)
        used_week = parse_sum(res_week)
        used_month = parse_sum(res_month)
        used_total = parse_sum(res_total)

        return {
            "updated_at": updated_at,
            "total_provider_space": total_provider_space,
            "used_provider_space": used_provider_space,
            "used_today": used_today,
            "used_week": used_week,
            "used_month": used_month,
            "used_total": used_total,
        }

    async def sum_wallet_earned_between(
        self,
        pubkey: str,
        start_date: date,
        end_date: date,
    ) -> int:
        stmt = select(func.sum(ProviderWalletHistoryModel.earned)).where(
            ProviderWalletHistoryModel.provider_pubkey == pubkey,
            ProviderWalletHistoryModel.date >= start_date,
            ProviderWalletHistoryModel.date <= end_date,
        )
        res = await self.session.execute(stmt)
        return int(res.scalar() or 0)

    async def sum_traffic_between(
        self,
        pubkey: str,
        start_date: date,
        end_date: date,
    ) -> tuple[int, int]:
        stmt = select(
            func.sum(ProviderTrafficHistoryModel.traffic_in),
            func.sum(ProviderTrafficHistoryModel.traffic_out),
        ).where(
            ProviderTrafficHistoryModel.provider_pubkey == pubkey,
            ProviderTrafficHistoryModel.date >= start_date,
            ProviderTrafficHistoryModel.date <= end_date,
        )
        res = await self.session.execute(stmt)
        row = res.first()
        s_in = int((row[0] or 0) if row else 0)
        s_out = int((row[1] or 0) if row else 0)
        return s_in, s_out

    async def sum_storage_used_between(
        self,
        pubkey: str,
        start_date: date,
        end_date: date,
    ) -> t.Tuple[float, t.Optional[float], t.Optional[float]]:
        sum_stmt = select(func.sum(ProviderStorageHistoryModel.used_daily_space)).where(
            ProviderStorageHistoryModel.provider_pubkey == pubkey,
            ProviderStorageHistoryModel.date >= start_date,
            ProviderStorageHistoryModel.date <= end_date,
        )
        res = await self.session.execute(sum_stmt)
        used_sum_gb = float(res.scalar() or 0.0)

        snapshot_stmt = (
            select(
                ProviderStorageHistoryModel.total_provider_space,
                ProviderStorageHistoryModel.used_provider_space,
            )
            .where(
                ProviderStorageHistoryModel.provider_pubkey == pubkey,
                ProviderStorageHistoryModel.date <= end_date,
            )
            .order_by(ProviderStorageHistoryModel.date.desc())
            .limit(1)
        )
        snap_res = await self.session.execute(snapshot_stmt)
        snap = snap_res.first()

        total_gb = float(snap[0]) if snap and snap[0] is not None else None
        used_gb = float(snap[1]) if snap and snap[1] is not None else None

        return used_sum_gb, total_gb, used_gb
