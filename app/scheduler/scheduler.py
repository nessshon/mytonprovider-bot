from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from . import tasks
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
            tasks.monitor_providers_job,
            trigger=IntervalTrigger(seconds=30),
            kwargs={"ctx": ctx},
            id=tasks.monitor_providers_job.__name__,
            misfire_grace_time=30,
            coalesce=True,
            max_instances=1,
            replace_existing=True,
        )
        self.async_scheduler.add_job(
            tasks.monitor_balances_job,
            trigger=IntervalTrigger(seconds=60),
            kwargs={"ctx": ctx},
            id=tasks.monitor_balances_job.__name__,
            misfire_grace_time=30,
            coalesce=True,
            max_instances=1,
            replace_existing=True,
        )

    def remove_jobs(self) -> None:
        self.async_scheduler.remove_job(tasks.monitor_providers_job.__name__)
        self.async_scheduler.remove_job(tasks.monitor_balances_job.__name__)
