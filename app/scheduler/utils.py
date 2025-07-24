import typing as t
from datetime import datetime

from redis.asyncio import Redis

from ..config import TIMEZONE
from ..database.models import (
    TelemetryModel,
)
from ..utils.mtpapi import MyTONProviderAPI
from ..utils.mtpapi.models import ProviderSearchPayload, Provider
from ..utils.toncenter import TONCenterAPI
from ..utils.toncenter.models import AccountStatesResponse

REDIS_HISTORY_PREFIX = "telemetry:history"


async def iterate_providers(
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


async def create_telemetry_snapshot(
        redis: Redis,
        telemetry: TelemetryModel,
) -> None:
    now = datetime.now(TIMEZONE)
    day_str = now.date().isoformat()
    key = f"{REDIS_HISTORY_PREFIX}:{telemetry.provider_pubkey}:{day_str}"

    await redis.set(
        name=key,
        value=telemetry.model_dump_json(),
        ex=60 * 60 * 24 * 30,
    )


async def get_provider_balance(toncenterapi: TONCenterAPI, address: str) -> int:
    async with toncenterapi:
        response: AccountStatesResponse = await toncenterapi.account_state(address)
        return int(response.accounts[0].balance)
