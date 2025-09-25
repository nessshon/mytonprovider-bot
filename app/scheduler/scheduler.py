from apscheduler.events import EVENT_JOB_ERROR
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from . import jobs
from .errors import on_job_error
from ..config import TIMEZONE, SCHEDULER_URL
from ..context import get_context


class Scheduler:

    def __init__(self) -> None:
        self.async_scheduler: AsyncIOScheduler = AsyncIOScheduler(timezone=TIMEZONE)

    async def start(self) -> None:
        self.async_scheduler.add_jobstore(SQLAlchemyJobStore(SCHEDULER_URL))
        self.async_scheduler.add_listener(on_job_error, mask=EVENT_JOB_ERROR)
        self.async_scheduler.start()
        self.add_jobs()

    async def shutdown(self) -> None:
        self.remove_jobs()
        self.async_scheduler.shutdown(wait=False)

    def add_jobs(self) -> None:
        ctx = get_context()

        self.async_scheduler.add_job(
            jobs.sync_providers_job,
            trigger=CronTrigger(minute="*"),
            kwargs={"ctx": ctx},
            id=jobs.sync_providers_job.__name__,
            misfire_grace_time=30,
            coalesce=True,
            max_instances=1,
            replace_existing=True,
        )
        self.async_scheduler.add_job(
            jobs.alerts_dispatch_job,
            trigger=CronTrigger(minute="*", jitter=30),
            kwargs={"ctx": ctx},
            id=jobs.alerts_dispatch_job.__name__,
            misfire_grace_time=30,
            coalesce=True,
            max_instances=1,
            replace_existing=True,
        )
        self.async_scheduler.add_job(
            jobs.update_wallets_job,
            trigger=CronTrigger(minute="*/5", jitter=60),
            kwargs={"ctx": ctx},
            id=jobs.update_wallets_job.__name__,
            misfire_grace_time=300,
            coalesce=True,
            max_instances=1,
            replace_existing=True,
        )
        self.async_scheduler.add_job(
            jobs.monthly_report_job,
            trigger=CronTrigger(
                day=1,
                hour=12,
                minute=0,
                timezone=TIMEZONE,
            ),
            kwargs={"ctx": ctx},
            id=jobs.monthly_report_job.__name__,
            misfire_grace_time=3600,
            coalesce=True,
            max_instances=1,
            replace_existing=True,
        )

    def remove_jobs(self) -> None:
        self.async_scheduler.remove_job(jobs.sync_providers_job.__name__)
        self.async_scheduler.remove_job(jobs.alerts_dispatch_job.__name__)
        self.async_scheduler.remove_job(jobs.update_wallets_job.__name__)
        self.async_scheduler.remove_job(jobs.monthly_report_job.__name__)
