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

    cutoff = (now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    sql_text = text(
        """
        DELETE FROM providers_history AS t
        WHERE t.archived_at < :cutoff
          AND EXISTS (
            SELECT 1
            FROM providers_history AS keep
            WHERE keep.pubkey = t.pubkey
              AND keep.archived_at < :cutoff
              AND substr(keep.archived_at, 1, 13) = substr(t.archived_at, 1, 13)
              AND keep.archived_at > t.archived_at
          )
    """
    )
    await uow.session.execute(sql_text, {"cutoff": cutoff})


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
