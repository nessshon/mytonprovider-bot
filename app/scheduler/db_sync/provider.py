import typing as t

from ...database import UnitOfWork
from ...database.models import ProviderModel
from ...utils.mtpapi import MyTONProviderAPI
from ...utils.mtpapi.models import ProviderSearchPayload, Provider


async def sync_providers(uow: UnitOfWork, mtpapi: MyTONProviderAPI) -> None:
    async for provider in _iterate_providers(mtpapi):
        model = ProviderModel(
            pubkey=provider.pubkey.lower(),
            address=provider.address,
            uptime=provider.uptime,
            working_time=provider.working_time,
            rating=provider.rating,
            max_span=provider.max_span,
            min_span=provider.min_span,
            price=provider.price,
            max_bag_size_bytes=provider.max_bag_size_bytes,
            reg_time=provider.reg_time,
            status=provider.status or 0,
            is_send_telemetry=provider.is_send_telemetry,
            telemetry_raw=provider.telemetry.model_dump() if provider.telemetry else {},
        )

        await uow.provider.upsert(model)

        if not provider.is_send_telemetry:
            await uow.telemetry.delete(provider_pubkey=provider.pubkey)


async def _iterate_providers(
    mtpapi: MyTONProviderAPI,
    limit: int = 100,
) -> t.AsyncGenerator[Provider, None]:
    offset = 0
    while True:
        response = await mtpapi.providers.search(
            payload=ProviderSearchPayload(offset=offset, limit=limit)
        )
        if not response.providers:
            break
        for provider in response.providers:
            yield provider
        offset += limit
