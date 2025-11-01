import logging
import typing as t
from datetime import timedelta

from sqlalchemy.sql.expression import text

from ....api.mytonprovider import MytonproviderClient, Provider, ProviderSearchPayload
from ....context import Context
from ....database.helpers import now_rounded_min
from ....database.models import ProviderModel, ProviderHistoryModel
from ....database.unitofwork import UnitOfWork

logger = logging.getLogger(__name__)


async def iterate_providers(
    mytonprovider: MytonproviderClient,
    limit: int = 100,
) -> t.AsyncGenerator[Provider, None]:
    offset = 0
    while True:
        payload = ProviderSearchPayload(offset=offset, limit=limit)
        response = await mytonprovider.providers.search(payload=payload)
        if not response.providers:
            break
        for provider in response.providers:
            yield provider
        offset += limit


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


async def update_providers_job(ctx: Context) -> None:
    uow = UnitOfWork(ctx.db.session_factory)
    now = now_rounded_min()

    provider_models = []
    provider_history_models = []
    async for provider in iterate_providers(ctx.mytonprovider):
        data = provider.model_dump()

        provider_data = data.copy()
        provider_history_data = data.copy()

        provider_data["updated_at"] = now
        provider_models.append(ProviderModel(**provider_data))

        provider_history_data["archived_at"] = now
        provider_history_models.append(ProviderHistoryModel(**provider_history_data))

    async with uow:
        await uow.provider.bulk_upsert(provider_models)
        await uow.provider_history.bulk_upsert(provider_history_models)
    async with uow:
        await downsample_history_hourly(uow)
