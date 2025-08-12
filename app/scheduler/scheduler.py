from apscheduler.events import EVENT_JOB_ERROR
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

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

        for job_func, interval in [
            (jobs.monitor_providers_job, 60),
            (jobs.monitor_balances_job, 90),
            (jobs.monitor_traffics_job, 120),
        ]:
            job_id = job_func.__name__
            self.async_scheduler.add_job(
                job_func,
                trigger=IntervalTrigger(seconds=interval),
                kwargs={"ctx": ctx},
                id=job_id,
                misfire_grace_time=30,
                coalesce=True,
                max_instances=1,
                replace_existing=True,
            )

    def remove_jobs(self) -> None:
        for job_id in (
            jobs.monitor_providers_job.__name__,
            jobs.monitor_balances_job.__name__,
            jobs.monitor_traffics_job.__name__,
        ):
            self.async_scheduler.remove_job(job_id)
