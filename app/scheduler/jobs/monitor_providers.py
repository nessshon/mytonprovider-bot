import logging
import typing as t

from sqlalchemy.sql.expression import delete

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

    async with uow:
        total_from_db = await uow.telemetry.all()

    db_map = {row.provider_pubkey.lower(): row for row in total_from_db}

    for telemetry in response.providers:
        pubkey = telemetry.storage.provider.pubkey.lower()
        telemetry_raw_data = telemetry.model_dump()

        prev_telemetry: t.Optional[TelemetryModel] = None
        if pubkey in db_map:
            prev_telemetry = TelemetryModel(**db_map[pubkey].model_dump())
            db_map.pop(pubkey, None)

        async with uow:
            curr_telemetry = await uow.telemetry.upsert(
                TelemetryModel(
                    **telemetry_raw_data,
                    raw=telemetry_raw_data,
                    provider_pubkey=pubkey,
                )
            )

        telemetries.append((prev_telemetry, curr_telemetry))

    missing_pubkeys = list(db_map.keys())
    deleted_count = 0
    if missing_pubkeys:
        async with uow:
            res = await uow.session.execute(
                delete(TelemetryModel).where(
                    TelemetryModel.provider_pubkey.in_(missing_pubkeys)
                )
            )
            deleted_count = res.rowcount or 0

    logger.info(
        f"Retrieved {total_from_api} providers from API, "
        f"upserted: {len(telemetries)} into the database, "
        f"deleted: {deleted_count}"
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
        (
            provider,
            (
                telemetry_map[provider.pubkey]
                if provider.pubkey in telemetry_map
                else (None, None)
            ),
        )
        for provider in providers
    ]

    for provider, (prev_telemetry, curr_telemetry) in provider_telemetry_pairs:
        alert_manager = AlertManager(ctx)
        await alert_manager.dispatch(
            provider=provider,
            curr_telemetry=curr_telemetry,
            prev_telemetry=prev_telemetry,
        )
