import logging
import typing as t

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
