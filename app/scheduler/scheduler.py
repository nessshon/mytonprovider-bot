from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .tasks import (
    monitor_providers_and_telemetry_job,
    save_telemetry_jostory_job,
)
from ..config import TIMEZONE, SCHEDULER_URL
from ..context import get_context


class Scheduler:

    def __init__(self) -> None:
        self.async_scheduler: AsyncIOScheduler = AsyncIOScheduler(timezone=TIMEZONE)

    async def start(self) -> None:
        self.async_scheduler.add_jobstore(SQLAlchemyJobStore(SCHEDULER_URL))
        self.async_scheduler.start()
        self.add_jobs()

    async def shutdown(self) -> None:
        self.remove_jobs()
        self.async_scheduler.shutdown(wait=False)

    def add_jobs(self) -> None:
        ctx = get_context()

        self.async_scheduler.add_job(
            monitor_providers_and_telemetry_job,
            trigger=IntervalTrigger(seconds=20),
            kwargs={"ctx": ctx},
            id=monitor_providers_and_telemetry_job.__name__,
            misfire_grace_time=30,
            coalesce=True,
            replace_existing=True,
        )
        self.async_scheduler.add_job(
            save_telemetry_jostory_job,
            trigger=IntervalTrigger(hours=1),
            kwargs={"ctx": ctx},
            id=save_telemetry_jostory_job.__name__,
            replace_existing=True,
        )

    def remove_jobs(self) -> None:
        self.async_scheduler.remove_job(monitor_providers_and_telemetry_job.__name__)
        self.async_scheduler.remove_job(save_telemetry_jostory_job.__name__)
