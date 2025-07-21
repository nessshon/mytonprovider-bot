from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .provider import sync_providers
from .telemetry import sync_telemetry
from .telemetry_history import sync_telemetry_history
from ...context import Context, get_context
from ...database import UnitOfWork


class DBSyncJob:
    SYNC_JOB_ID = "sync_provider_and_telemetry"
    HISTORY_JOB_ID = "save_telemetry_history"

    @classmethod
    async def run_sync(cls, ctx: Context) -> None:
        uow = UnitOfWork(ctx.db.session_factory)
        async with uow:
            async with ctx.mtpapi:
                await sync_providers(uow, ctx.mtpapi)
                await sync_telemetry(uow, ctx.redis, ctx.mtpapi)

    @classmethod
    def add_jobs(cls, scheduler: AsyncIOScheduler) -> None:
        ctx = get_context()

        scheduler.add_job(
            cls.run_sync,
            trigger=IntervalTrigger(seconds=60),
            kwargs={"ctx": ctx},
            id=cls.SYNC_JOB_ID,
            misfire_grace_time=30,
            coalesce=True,
            replace_existing=True,
        )

        scheduler.add_job(
            sync_telemetry_history,
            trigger=IntervalTrigger(hours=1),
            kwargs={"ctx": ctx},
            id=cls.HISTORY_JOB_ID,
            replace_existing=True,
        )

    @classmethod
    def remove_jobs(cls, scheduler: AsyncIOScheduler) -> None:
        scheduler.remove_job(cls.SYNC_JOB_ID)
        scheduler.remove_job(cls.HISTORY_JOB_ID)
