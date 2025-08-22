# handlers/scheduler_errors.py
import asyncio
import logging
from typing import Union

from aiogram.types import BufferedInputFile
from aiogram.utils.markdown import hbold, hcode
from apscheduler.events import (
    JobEvent,
    JobExecutionEvent,
    EVENT_JOB_MISSED,
)

from ..bot import Broadcaster
from ..config import DEV_ID
from ..context import Context, get_context

logger = logging.getLogger(__name__)


async def _handle_job_event(
    event: Union[JobExecutionEvent, JobEvent],
    ctx: Context,
) -> None:
    broadcaster: Broadcaster = ctx.broadcaster
    job_id = getattr(event, "job_id", "unknown")

    if isinstance(event, JobExecutionEvent) and event.exception:
        exc = event.exception
        exc_type = type(exc).__name__
        exc_text = str(exc).strip().split("\n")[0]

        logger.error(
            "Unhandled error in scheduler job. "
            f"Job ID: {job_id}; Exception Type: {exc_type}; Exception: {exc_text}"
        )

        caption = f"{hbold(exc_type)}: {hcode(exc_text[:900])}"
        traceback_text = event.traceback or "No traceback available"
        document = BufferedInputFile(
            traceback_text.encode(), filename=f"error_{job_id}.txt"
        )
        await broadcaster.send_document(DEV_ID, document, caption=caption)
        return

    if event.code == EVENT_JOB_MISSED:
        scheduled = getattr(event, "scheduled_run_time", None)
        when = str(scheduled) if scheduled else "unknown"
        text = f"⏰ MISSED job: {hcode(job_id)}\n" f"scheduled_run_time: {hcode(when)}"
        logger.warning(f"Job MISSED. Job ID: {job_id}; scheduled_run_time: {when}")
        await broadcaster.send_message(DEV_ID, text)
        return

    return


def on_job_event(event) -> None:
    ctx: Context = get_context()
    loop = asyncio.get_event_loop()
    loop.create_task(_handle_job_event(event, ctx))
