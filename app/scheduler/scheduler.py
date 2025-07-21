from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .db_sync import DBSyncJob
from ..config import TIMEZONE, SCHEDULER_URL


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
        DBSyncJob.add_jobs(self.async_scheduler)

    def remove_jobs(self) -> None:
        DBSyncJob.remove_jobs(self.async_scheduler)
