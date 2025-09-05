from __future__ import annotations

import logging
from datetime import datetime, date as date_type

from ...config import TIMEZONE
from ...context import Context
from ...database import UnitOfWork
from ...database.models import ProviderStorageHistoryModel

logger = logging.getLogger(__name__)


async def monitor_storage_job(ctx: Context) -> None:
    uow = UnitOfWork(ctx.db.session_factory)

    async with uow:
        providers = await uow.provider.all()

    today: date_type = datetime.now(TIMEZONE).date()
    now = datetime.now(TIMEZONE)

    for provider in providers:
        pubkey = provider.pubkey
        telemetry = provider.telemetry

        used_gb = telemetry.used_provider_space
        total_gb = telemetry.total_provider_space

        if used_gb is None:
            logger.info(f"Skipped {pubkey} — no used_provider_space in telemetry")
            continue

        async with uow:
            last_row = await uow.provider_storage_history.get(
                provider_pubkey=pubkey,
                order_by=ProviderStorageHistoryModel.date.desc(),
            )

            if last_row is None:
                await uow.provider_storage_history.upsert(
                    ProviderStorageHistoryModel(
                        provider_pubkey=pubkey,
                        date=today,
                        updated_at=now,
                        total_provider_space=total_gb,
                        used_provider_space=used_gb,
                        used_daily_space=used_gb,
                    )
                )
                continue

            if last_row.date != today:
                prev_used = last_row.used_provider_space or 0.0
                day_delta = used_gb - prev_used
                await uow.provider_storage_history.upsert(
                    ProviderStorageHistoryModel(
                        provider_pubkey=pubkey,
                        date=today,
                        updated_at=now,
                        total_provider_space=total_gb,
                        used_provider_space=used_gb,
                        used_daily_space=float(day_delta),
                    )
                )
                continue

            prev_snapshot_used = last_row.used_provider_space or 0.0
            increment = used_gb - prev_snapshot_used

            if increment != 0.0:
                last_row.used_daily_space += increment

            last_row.used_provider_space = used_gb
            last_row.total_provider_space = total_gb
            last_row.updated_at = now
            await uow.provider_storage_history.upsert(last_row)
