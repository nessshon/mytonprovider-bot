import typing as t
from datetime import datetime, timedelta

from aiogram.enums import ChatMemberStatus
from sqlalchemy import String, Float, select, func, and_, desc, cast
from sqlalchemy.ext.asyncio.session import AsyncSession

from app.config import TIMEZONE
from app.database.models import (
    WalletHistoryModel,
    TelemetryHistoryModel,
    TelemetryModel,
    ProviderModel,
    UserModel,
)


def _dt_range_for(
    period: str,
    today: datetime,
) -> tuple[t.Optional[datetime], datetime]:
    start_of_today = today.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "today":
        return start_of_today, today
    if period == "week":
        return start_of_today - timedelta(days=7), today
    if period == "month":
        return start_of_today - timedelta(days=30), today
    if period == "total":
        return None, today
    raise ValueError("bad period")


def _month_bounds_now() -> tuple[datetime, datetime, str, str]:
    now = datetime.now(TIMEZONE)
    first_this = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if first_this.month == 1:
        first_prev = first_this.replace(year=first_this.year - 1, month=12)
    else:
        first_prev = first_this.replace(month=first_this.month - 1)
    end_display = (first_this - timedelta(days=1)).date().isoformat()
    start_display = first_prev.date().isoformat()
    return first_prev, first_this, start_display, end_display


async def _count_git_hashes(session: AsyncSession, key: str) -> dict[str, int]:
    rows = (
        await session.execute(
            select(
                cast(TelemetryModel.git_hashes[key].as_string(), String).label("h"),
                func.count().label("c"),
            )
            .where(TelemetryModel.git_hashes[key].isnot(None))
            .group_by("h")
        )
    ).all()
    return {h: c for h, c in rows if h is not None}


async def build_provider_wallet_metrics(session: AsyncSession, pubkey: str) -> dict:
    now = datetime.now(TIMEZONE)

    last_row_stmt = (
        select(WalletHistoryModel.balance, WalletHistoryModel.archived_at)
        .where(WalletHistoryModel.provider_pubkey == pubkey)
        .order_by(desc(WalletHistoryModel.archived_at))
        .limit(1)
    )
    last_row = (await session.execute(last_row_stmt)).first()
    balance = last_row[0] if last_row else 0
    updated_at = last_row[1] if last_row else None

    async def _sum_earned(start: datetime | None, end: datetime) -> int:
        stmt = select(func.coalesce(func.sum(WalletHistoryModel.earned), 0)).where(
            WalletHistoryModel.provider_pubkey == pubkey
        )
        if start is not None:
            stmt = stmt.where(WalletHistoryModel.archived_at >= start)
        stmt = stmt.where(WalletHistoryModel.archived_at < end)
        return (await session.execute(stmt)).scalar_one()

    start_today, end_today = _dt_range_for("today", now)
    start_week, _ = _dt_range_for("week", now)
    start_month, _ = _dt_range_for("month", now)

    earned_today = await _sum_earned(start_today, now)
    earned_week = await _sum_earned(start_week, now)
    earned_month = await _sum_earned(start_month, now)
    earned_total = await _sum_earned(None, now)

    return {
        "balance": balance,
        "earned_today": earned_today,
        "earned_week": earned_week,
        "earned_month": earned_month,
        "earned_total": earned_total,
        "updated_at": updated_at,
    }


async def build_provider_traffic_metrics(session: AsyncSession, pubkey: str) -> dict:
    now = datetime.now(TIMEZONE)

    async def _delta_for(period: str) -> tuple[int, int, datetime | None]:
        start, end = _dt_range_for(period, now)
        base = TelemetryHistoryModel
        conds = [base.provider_pubkey == pubkey]
        if start is not None:
            conds.append(base.archived_at >= start)
        conds.append(base.archived_at < end)

        stmt = select(
            func.coalesce(func.max(base.bytes_recv), 0).label("max_in"),
            func.coalesce(func.min(base.bytes_recv), 0).label("min_in"),
            func.coalesce(func.max(base.bytes_sent), 0).label("max_out"),
            func.coalesce(func.min(base.bytes_sent), 0).label("min_out"),
            func.max(base.archived_at).label("last_ts"),
        ).where(and_(*conds))

        row = (await session.execute(stmt)).mappings().one()
        delta_in = int(row["max_in"] - row["min_in"])
        delta_out = int(row["max_out"] - row["min_out"])
        return max(delta_in, 0), max(delta_out, 0), row["last_ts"]

    ti, to, updated = await _delta_for("today")
    wi, wo, _ = await _delta_for("week")
    mi, mo, _ = await _delta_for("month")
    ai, ao, _ = await _delta_for("total")

    return {
        "traffic_today_in": ti,
        "traffic_today_out": to,
        "traffic_today_total": ti + to,
        "traffic_week_in": wi,
        "traffic_week_out": wo,
        "traffic_week_total": wi + wo,
        "traffic_month_in": mi,
        "traffic_month_out": mo,
        "traffic_month_total": mi + mo,
        "traffic_total_in": ai,
        "traffic_total_out": ao,
        "traffic_total": ai + ao,
        "updated_at": updated,
    }


async def build_provider_storage_metrics(session: AsyncSession, pubkey: str) -> dict:
    now = datetime.now(TIMEZONE)
    th_model = TelemetryHistoryModel

    provider_obj = th_model.storage.op("->")("provider")
    used_expr = cast(provider_obj.op("->>")("used_provider_space"), Float)
    total_expr = cast(provider_obj.op("->>")("total_provider_space"), Float)

    async def _delta_used(period: str) -> float:
        start, end = _dt_range_for(period, now)
        conds = [th_model.provider_pubkey == pubkey]
        if start is not None:
            conds.append(th_model.archived_at >= start)
        conds.append(th_model.archived_at < end)

        stmt = select(
            (
                func.coalesce(func.max(used_expr), 0.0)
                - func.coalesce(func.min(used_expr), 0.0)
            ).label("delta"),
        ).where(and_(*conds))

        return float((await session.execute(stmt)).scalar_one())

    last_stmt = (
        select(used_expr.label("used"), total_expr.label("total"), th_model.archived_at)
        .where(th_model.provider_pubkey == pubkey)
        .order_by(desc(th_model.archived_at))
        .limit(1)
    )
    last = (await session.execute(last_stmt)).mappings().first()
    used_eom = float(last["used"]) if last and last["used"] is not None else 0.0
    total_eom = float(last["total"]) if last and last["total"] is not None else 0.0
    updated_at = last["archived_at"] if last else None

    return {
        "used_today": await _delta_used("today"),
        "used_week": await _delta_used("week"),
        "used_month": await _delta_used("month"),
        "used_total": await _delta_used("total"),
        "used_provider_space": used_eom,
        "total_provider_space": total_eom,
        "updated_at": updated_at,
    }


async def build_stats_summary(session: AsyncSession) -> t.Dict[str, t.Any]:
    users_total = await session.scalar(select(func.count()).select_from(UserModel))
    users_active = await session.scalar(
        select(func.count())
        .select_from(UserModel)
        .where(UserModel.state.in_({ChatMemberStatus.MEMBER}))
    )
    users_inactive = max(users_total - users_active, 0)

    providers_total = await session.scalar(
        select(func.count()).select_from(ProviderModel)
    )
    providers_with_telemetry = await session.scalar(
        select(func.count()).select_from(TelemetryModel)
    )

    providers_with_password = await session.scalar(
        select(func.count())
        .select_from(TelemetryModel)
        .where(TelemetryModel.telemetry_pass.is_not(None))
    )

    storage_git_hashes = await _count_git_hashes(session, "ton-storage")
    provider_git_hashes = await _count_git_hashes(session, "ton-storage-provider")

    return {
        "users_total": users_total,
        "users_active": users_active,
        "users_inactive": users_inactive,
        "providers_total": providers_total,
        "providers_with_telemetry": providers_with_telemetry,
        "providers_with_password": providers_with_password,
        "storage_git_hashes": dict(storage_git_hashes),
        "provider_git_hashes": dict(provider_git_hashes),
    }


async def build_monthly_report(
    session: AsyncSession,
    pubkey: str,
) -> t.Dict[str, t.Any]:
    start_dt, end_dt, start_disp, end_disp = _month_bounds_now()
    th, wh = TelemetryHistoryModel, WalletHistoryModel

    earned = await session.scalar(
        select(func.coalesce(func.sum(wh.earned), 0))
        .where(wh.provider_pubkey == pubkey)
        .where(wh.archived_at >= start_dt, wh.archived_at < end_dt)
    )

    traffic_row = (
        (
            await session.execute(
                select(
                    func.coalesce(func.max(th.bytes_recv), 0).label("max_in"),
                    func.coalesce(func.min(th.bytes_recv), 0).label("min_in"),
                    func.coalesce(func.max(th.bytes_sent), 0).label("max_out"),
                    func.coalesce(func.min(th.bytes_sent), 0).label("min_out"),
                )
                .where(th.provider_pubkey == pubkey)
                .where(th.archived_at >= start_dt, th.archived_at < end_dt)
            )
        )
        .mappings()
        .one()
    )
    traffic_in_bytes = max(int(traffic_row["max_in"] - traffic_row["min_in"]), 0)
    traffic_out_bytes = max(int(traffic_row["max_out"] - traffic_row["min_out"]), 0)

    provider_obj = th.storage.op("->")("provider")
    used_expr = cast(provider_obj.op("->>")("used_provider_space"), Float)
    used_delta_gb = await session.scalar(
        select(
            (
                func.coalesce(func.max(used_expr), 0.0)
                - func.coalesce(func.min(used_expr), 0.0)
            ).label("delta")
        )
        .where(th.provider_pubkey == pubkey)
        .where(th.archived_at >= start_dt, th.archived_at < end_dt)
    )
    used_space_bytes = int(max(used_delta_gb, 0.0) * 1_000_000_000)

    return {
        "start_date": start_disp,
        "end_date": end_disp,
        "earned_nanoton": int(earned),
        "used_space_bytes": used_space_bytes,
        "traffic_in_bytes": traffic_in_bytes,
        "traffic_out_bytes": traffic_out_bytes,
    }
