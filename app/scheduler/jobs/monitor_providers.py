import logging
import typing as t

from ...context import Context
from ...database import UnitOfWork
from ...database.models import (
    ProviderModel,
    ProviderTelemetryModel,
)
from ...database.models import TelemetryModel
from ...utils.alerts.manager import AlertManager
from ...utils.mtpapi import MyTONProviderAPI
from ...utils.mtpapi.models import Provider, ProviderSearchPayload

logger = logging.getLogger(__name__)


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
    total_from_api = 0

    async for provider in _iterate_providers(mtpapi):
        total_from_api += 1
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

    logger.info(
        f"Retrieved {total_from_api} providers from API, "
        f"upserted: {len(providers)} into the database"
    )
    return providers


async def sync_telemetries(
    uow: UnitOfWork,
    mtpapi: MyTONProviderAPI,
) -> t.List[t.Tuple[t.Optional[TelemetryModel], TelemetryModel]]:
    telemetries: list[tuple[t.Optional[TelemetryModel], TelemetryModel]] = []
    response = await mtpapi.telemetry()
    total_from_api = len(response.providers)

    for telemetry in response.providers:
        pubkey = telemetry.storage.provider.pubkey.lower()
        telemetry_raw_data = telemetry.model_dump()

        async with uow:
            prev_telemetry = await uow.telemetry.get(provider_pubkey=pubkey)
            if prev_telemetry is not None:
                prev_telemetry_dict = prev_telemetry.model_dump()
                prev_telemetry = TelemetryModel(**prev_telemetry_dict)

        async with uow:
            curr_telemetry = await uow.telemetry.upsert(
                TelemetryModel(
                    **telemetry_raw_data,
                    raw=telemetry_raw_data,
                    provider_pubkey=pubkey,
                )
            )

        telemetries.append((prev_telemetry, curr_telemetry))

    logger.info(
        f"Retrieved {total_from_api} telemetry from API, "
        f"upserted: {len(telemetries)} into the database"
    )
    return telemetries


async def monitor_providers_job(ctx: Context) -> None:
    uow = UnitOfWork(ctx.db.session_factory)
    mtpapi: MyTONProviderAPI = ctx.mtpapi

    try:
        async with mtpapi:
            try:
                providers = await sync_providers(uow, mtpapi)
            except Exception:
                logger.exception(f"Failed to sync providers")
                raise

            try:
                telemetries = await sync_telemetries(uow, mtpapi)
            except Exception:
                logger.exception(f"Failed to sync telemetries")
                raise
    except Exception:
        logger.exception(f"Failed to connect or sync via MTP API")
        raise

    telemetry_map = {curr.provider_pubkey: (prev, curr) for (prev, curr) in telemetries}

    provider_telemetry_pairs = [
        (provider, telemetry_map[provider.pubkey])
        for provider in providers
        if provider.pubkey in telemetry_map
    ]

    for provider, (prev_telemetry, curr_telemetry) in provider_telemetry_pairs:
        alert_manager = AlertManager(ctx)
        await alert_manager.dispatch(
            provider=provider,
            curr_telemetry=curr_telemetry,
            prev_telemetry=prev_telemetry,
        )
