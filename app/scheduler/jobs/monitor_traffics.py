from __future__ import annotations

import logging
import typing as t
from datetime import datetime, timedelta, date as date_type

from sqlalchemy.orm import Mapped

from ...config import TIMEZONE
from ...context import Context
from ...database import UnitOfWork
from ...database.models import ProviderTrafficHistoryModel

logger = logging.getLogger(__name__)


async def monitor_traffics_job(ctx: Context) -> None:
    uow = UnitOfWork(ctx.db.session_factory)

    async with uow:
        telemetry_list = await uow.telemetry.all()

    for telemetry in telemetry_list:
        pubkey = telemetry.provider_pubkey
        curr_recv = telemetry.bytes_recv
        curr_sent = telemetry.bytes_sent

        if curr_recv is None or curr_sent is None:
            logger.info(f"Skipped {pubkey} — no traffic counters")
            continue

        now = datetime.now(TIMEZONE)
        today: date_type = now.date()

        def delta(curr: int, last: t.Optional[Mapped[int]] = None) -> int:
            if last is None:
                return curr
            d = curr - last
            return curr if d < 0 else (d if d > 0 else 0)

        async with uow:
            today_row = await uow.provider_traffic_history.get(
                provider_pubkey=pubkey, date=today
            )

            if today_row is None:
                prev_row = None
                day = today - timedelta(days=1)
                for _ in range(7):
                    prev_row = await uow.provider_traffic_history.get(
                        provider_pubkey=pubkey, date=day
                    )
                    if prev_row:
                        break
                    day -= timedelta(days=1)

                if prev_row is None:
                    await uow.provider_traffic_history.upsert(
                        ProviderTrafficHistoryModel(
                            provider_pubkey=pubkey,
                            date=today,
                            updated_at=now,
                            traffic_in=curr_recv,
                            traffic_out=curr_sent,
                            last_bytes_recv=curr_recv,
                            last_bytes_sent=curr_sent,
                        )
                    )
                    logger.info(f"Created first traffic record for {pubkey} (today)")
                    continue

                dr = delta(curr_recv, prev_row.last_bytes_recv)
                ds = delta(curr_sent, prev_row.last_bytes_sent)
                if dr:
                    prev_row.traffic_in += dr
                if ds:
                    prev_row.traffic_out += ds
                prev_row.last_bytes_recv = curr_recv
                prev_row.last_bytes_sent = curr_sent
                prev_row.updated_at = now
                await uow.provider_traffic_history.upsert(prev_row)

                await uow.provider_traffic_history.upsert(
                    ProviderTrafficHistoryModel(
                        provider_pubkey=pubkey,
                        date=today,
                        updated_at=now,
                        traffic_in=0,
                        traffic_out=0,
                        last_bytes_recv=curr_recv,
                        last_bytes_sent=curr_sent,
                    )
                )
                logger.info(f"Backfilled previous day and created today for {pubkey}")
                continue

            dr = delta(curr_recv, today_row.last_bytes_recv)
            ds = delta(curr_sent, today_row.last_bytes_sent)
            if dr:
                today_row.traffic_in += dr
            if ds:
                today_row.traffic_out += ds
            today_row.last_bytes_recv = curr_recv
            today_row.last_bytes_sent = curr_sent
            today_row.updated_at = now
            await uow.provider_traffic_history.upsert(today_row)
            logger.info(f"Updated today record for {pubkey}")
