import typing as t

from ...context import Context
from ...database import UnitOfWork
from ...database.models import (
    ProviderModel,
    ProviderTelemetryModel,
)
from ...database.models import TelemetryModel
from ...utils.alerts import AlertManager
from ...utils.mtpapi import MyTONProviderAPI
from ...utils.mtpapi.models import Provider, ProviderSearchPayload


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


async def sync_providers(
    uow: UnitOfWork,
    mtpapi: MyTONProviderAPI,
) -> t.List[ProviderModel]:
    providers = []

    async for provider in _iterate_providers(mtpapi):
        provider_pubkey = provider.pubkey.lower()

        provider_telemetry_raw_data = provider.telemetry.model_dump()
        provider_raw_data = provider.model_dump()

        provider_telemetry_data = {
            **provider_telemetry_raw_data,
            "provider_pubkey": provider_pubkey,
            "raw": provider_telemetry_raw_data,
        }
        provider_data = {
            **provider_raw_data,
            "pubkey": provider_pubkey,
            "raw": provider_raw_data,
            "telemetry": ProviderTelemetryModel(**provider_telemetry_data),
        }

        async with uow:
            model = ProviderModel(**provider_data)
            provider_model = await uow.provider.upsert(model)
        providers.append(provider_model)

    return providers


async def sync_telemetries(
    uow: UnitOfWork,
    mtpapi: MyTONProviderAPI,
) -> t.List[TelemetryModel]:
    telemetries = []
    response = await mtpapi.telemetry()

    for telemetry in response.providers:
        pubkey = telemetry.storage.provider.pubkey.lower()
        telemetry_raw_data = telemetry.model_dump()

        async with uow:
            model = TelemetryModel(
                **telemetry_raw_data,
                raw=telemetry_raw_data,
                provider_pubkey=pubkey,
            )
            telemetry_model = await uow.telemetry.upsert(model)
        telemetries.append(telemetry_model)

    return telemetries


async def monitor_providers_job(ctx: Context) -> None:
    uow = UnitOfWork(ctx.db.session_factory)
    mtpapi: MyTONProviderAPI = ctx.mtpapi

    async with mtpapi:
        providers = await sync_providers(uow, mtpapi)
        telemetries = await sync_telemetries(uow, mtpapi)

    telemetry_map: t.Dict[str, TelemetryModel] = {
        telemetry.provider_pubkey: telemetry for telemetry in telemetries
    }
    provider_telemetry_pairs: t.List[t.Tuple[ProviderModel, TelemetryModel]] = [
        (provider, telemetry_map[provider.pubkey])
        for provider in providers
        if provider.pubkey in telemetry_map
    ]

    for provider, telemetry in provider_telemetry_pairs:
        alert_manager = AlertManager(ctx)
        await alert_manager.dispatch(provider, telemetry)
