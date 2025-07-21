import json
from datetime import date, timedelta
from datetime import datetime

from redis.asyncio import Redis

from ...config import TIMEZONE
from ...context import Context
from ...database import UnitOfWork
from ...database.models import TelemetryHistoryModel, ProviderModel
from ...database.models import TelemetryModel

REDIS_HISTORY_PREFIX = "telemetry:history"


async def create_telemetry_snapshot(
    redis: Redis,
    telemetry: TelemetryModel,
) -> None:
    now = datetime.now(TIMEZONE)
    day_str = now.date().isoformat()
    key = f"{REDIS_HISTORY_PREFIX}:{telemetry.provider_pubkey}:{day_str}"

    telemetry_dict = telemetry.model_dump()
    telemetry_dict["updated_at"] = int(now.timestamp())

    await redis.set(name=key, value=json.dumps(telemetry_dict), ex=60 * 60 * 24 * 30)


async def sync_telemetry_history(ctx: Context) -> None:
    uow: UnitOfWork = UnitOfWork(ctx.db.session_factory)
    redis = ctx.redis

    yesterday: date = date.today() - timedelta(days=1)
    day_str = yesterday.isoformat()

    keys = await redis.keys(f"{REDIS_HISTORY_PREFIX}:*:{day_str}")
    if not keys:
        return

    for key in keys:
        data = await redis.get(key)
        if not data:
            continue

        raw = json.loads(data)
        pubkey = raw["provider_pubkey"]

        existing = await uow.telemetry_history.get(
            provider_pubkey=pubkey.lower(), date=yesterday
        )
        if existing:
            continue

        provider: ProviderModel = await uow.provider.get(pubkey=pubkey)
        price_per_200gb = provider.price if provider else 0.0
        max_bag_size = provider.max_bag_size_bytes if provider else 0

        used_provider_space = raw["provider_used_provider_space"]
        bags_count = int(used_provider_space / max_bag_size)

        ton_earned = round((used_provider_space / 200) * price_per_200gb, 6)

        history = TelemetryHistoryModel(
            provider_pubkey=pubkey.lower(),
            date=yesterday,
            used_provider_space=used_provider_space,
            total_provider_space=raw["provider_total_provider_space"],
            used_disk_space=raw["storage_used_disk_space"],
            total_disk_space=raw["storage_total_disk_space"],
            bags_count=bags_count,
            traffic_in=0.0,
            traffic_out=0.0,
            ton_balance=0.0,
            ton_earned=ton_earned,
        )

        await uow.telemetry_history.upsert(history)
