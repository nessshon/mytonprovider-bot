import typing as t
from datetime import date, timedelta, datetime

from redis.asyncio import Redis

from .utils import (
    iterate_providers,
    create_telemetry_snapshot,
    get_provider_balance,
    REDIS_HISTORY_PREFIX,
)
from ..config import TIMEZONE
from ..context import Context
from ..database import UnitOfWork
from ..database.models import (
    ProviderModel,
    ProviderTelemetryModel,
)
from ..database.models import (
    TelemetryModel,
    TelemetryHistoryModel,
)
from ..utils.alerts import AlertManager
from ..utils.mtpapi import MyTONProviderAPI


async def sync_providers(
        uow: UnitOfWork,
        mtpapi: MyTONProviderAPI,
) -> t.List[ProviderModel]:
    providers = []

    async for provider in iterate_providers(mtpapi):
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

        model = ProviderModel(**provider_data)
        provider_model = await uow.provider.upsert(model)
        providers.append(provider_model)

    return providers


async def sync_telemetries(
        redis: Redis,
        uow: UnitOfWork,
        mtpapi: MyTONProviderAPI,
) -> t.List[TelemetryModel]:
    telemetries = []
    response = await mtpapi.telemetry()

    for telemetry in response.providers:
        pubkey = telemetry.storage.provider.pubkey.lower()
        telemetry_raw_data = telemetry.model_dump()

        model = TelemetryModel(
            **telemetry_raw_data,
            raw=telemetry_raw_data,
            provider_pubkey=pubkey,
        )

        telemetry_model = await uow.telemetry.upsert(model)
        telemetries.append(telemetry_model)
        await create_telemetry_snapshot(redis, model)

    return telemetries


async def monitor_providers_and_telemetry_job(ctx: Context) -> None:
    uow = UnitOfWork(ctx.db.session_factory)
    mtpapi: MyTONProviderAPI = ctx.mtpapi
    async with uow:
        async with mtpapi:
            providers = await sync_providers(uow, mtpapi)
            telemetries = await sync_telemetries(ctx.redis, uow, mtpapi)

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


async def save_telemetry_jostory_job(ctx: Context) -> None:
    async with UnitOfWork(ctx.db.session_factory) as uow:
        yesterday: date = datetime.now(TIMEZONE).date() - timedelta(days=1)
        day_str = yesterday.isoformat()

        keys = await ctx.redis.keys(f"{REDIS_HISTORY_PREFIX}:*:{day_str}")
        if not keys:
            return

        for key in keys:
            data = await ctx.redis.get(key)
            if not data:
                continue

            telemetry = TelemetryModel.from_json(data)
            pubkey = telemetry.provider_pubkey

            if await uow.telemetry_history.get(provider_pubkey=pubkey, date=yesterday):
                continue

            provider: ProviderModel = await uow.provider.get(pubkey=pubkey)
            price_per_200gb = provider.price
            wallet_address = provider.address

            telemetry_storage = telemetry.storage
            max_bag_size_bytes = telemetry_storage["provider"]["max_bag_size_bytes"]
            used_provider_space = telemetry_storage["provider"]["used_provider_space"]
            total_provider_space = telemetry_storage["provider"]["total_provider_space"]

            # TODO: calculate traffic, bags, earnings
            traffic_in = 0
            traffic_out = 0
            bags_count = 0
            ton_earned = 0
            ton_balance = await get_provider_balance(ctx.toncenterapi, wallet_address)

            history = TelemetryHistoryModel(
                provider_pubkey=pubkey,
                date=yesterday,
                wallet_address=wallet_address,
                used_provider_space=used_provider_space,
                total_provider_space=total_provider_space,
                bags_count=bags_count,
                traffic_in=traffic_in,
                traffic_out=traffic_out,
                ton_balance=ton_balance,
                ton_earned=ton_earned,
            )

            await uow.telemetry_history.upsert(history)
