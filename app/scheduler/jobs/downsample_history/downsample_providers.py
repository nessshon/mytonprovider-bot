import asyncio
import logging
from datetime import timedelta

from sqlalchemy.sql.expression import text

from ....context import Context
from ....database.unitofwork import UnitOfWork

logger = logging.getLogger(__name__)

DOWNSAMPLE_TIMEOUT = 10 * 60


async def downsample_history_hourly(uow: UnitOfWork) -> None:
    from ....database.helpers import now

    start_prev_hour = (now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:00:00")
    end_prev_hour = (now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:00:00")

    sql = text(
        """
        WITH ranked AS (
          SELECT
            rowid,
            ROW_NUMBER() OVER (
              PARTITION BY pubkey
              ORDER BY archived_at DESC
            ) AS rn
          FROM providers_history
          WHERE archived_at >= :start_prev_hour
            AND archived_at <  :end_prev_hour
        )
        DELETE FROM providers_history
        WHERE rowid IN (SELECT rowid FROM ranked WHERE rn > 1);
        """
    )

    await uow.session.execute(
        sql,
        {
            "start_prev_hour": start_prev_hour,
            "end_prev_hour": end_prev_hour,
        },
    )


async def downsample_providers_job(ctx: Context) -> None:
    try:
        await asyncio.wait_for(
            _downsample_providers_impl(ctx),
            timeout=DOWNSAMPLE_TIMEOUT,
        )
    except asyncio.TimeoutError:
        logger.error(
            "downsample_providers_job timed out after %ss",
            DOWNSAMPLE_TIMEOUT,
        )
    except Exception:
        logger.exception("downsample_providers_job failed")
        raise


async def _downsample_providers_impl(ctx: Context) -> None:
    async with UnitOfWork(ctx.db.session_factory) as uow:
        await downsample_history_hourly(uow)
