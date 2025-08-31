from __future__ import annotations

import logging
import typing as t
from datetime import datetime, date as date_type

from sqlalchemy.orm.attributes import Mapped

from ...config import TIMEZONE
from ...context import Context
from ...database import UnitOfWork
from ...database.models import ProviderTrafficHistoryModel

logger = logging.getLogger(__name__)


def _delta(curr: int, last: t.Optional[Mapped[int]]) -> int:
    if last is None:
        return 0
    d = curr - last
    return curr if d < 0 else (d if d > 0 else 0)


async def monitor_traffics_job(ctx: Context) -> None:
    uow = UnitOfWork(ctx.db.session_factory)

    async with uow:
        telemetry_list = await uow.telemetry.all()

    today: date_type = datetime.now(TIMEZONE).date()
    now = datetime.now(TIMEZONE)

    for telemetry in telemetry_list:
        pubkey = telemetry.provider_pubkey
        curr_recv = telemetry.bytes_recv
        curr_sent = telemetry.bytes_sent

        if curr_recv is None or curr_sent is None:
            logger.info(f"Skipped {pubkey} — no traffic counters")
            continue

        async with uow:
            last_row = await uow.provider_traffic_history.get(
                order_by=ProviderTrafficHistoryModel.date.desc(),
                provider_pubkey=pubkey,
            )

            if last_row is None:
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
                logger.info(f"Created first traffic record for {pubkey} (today)")
                continue

            if last_row.date != today:
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
                logger.info(f"Created today record for {pubkey}")
                continue

            dr = _delta(curr_recv, last_row.last_bytes_recv)
            ds = _delta(curr_sent, last_row.last_bytes_sent)

            if dr:
                last_row.traffic_in += dr
            if ds:
                last_row.traffic_out += ds

            last_row.last_bytes_recv = curr_recv
            last_row.last_bytes_sent = curr_sent
            last_row.updated_at = now

            await uow.provider_traffic_history.upsert(last_row)
