import asyncio
import logging

from aiogram.types import BufferedInputFile
from aiogram.utils.markdown import hbold, hcode
from apscheduler.events import JobExecutionEvent

from ..bot import Broadcaster
from ..config import DEV_ID, ADMIN_IDS
from ..context import Context, get_context

logger = logging.getLogger(__name__)


async def _on_job_error(event: JobExecutionEvent, ctx: Context) -> None:
    exc = event.exception
    exc_type = type(exc).__name__
    exc_text = str(exc).strip().split("\n")[0]
    job_id = event.job_id or "unknown"

    logger.error(
        "Unhandled error in scheduler job. "
        f"Job ID: {job_id}; "
        f"Exception Type: {exc_type}; "
        f"Exception: {exc_text}"
    )

    broadcaster: Broadcaster = ctx.broadcaster
    caption = f"{hbold(exc_type)}: {hcode(exc_text[:900])}"

    traceback_text = event.traceback or "No traceback available"
    filename = f"error_{job_id}.txt"
    document = BufferedInputFile(traceback_text.encode(), filename=filename)

    for user_id in {DEV_ID, *ADMIN_IDS}:
        await broadcaster.send_document(user_id, document, caption=caption)
        await asyncio.sleep(0.3)


def on_job_error(event: JobExecutionEvent) -> None:
    ctx: Context = get_context()
    loop = asyncio.get_event_loop()
    loop.create_task(_on_job_error(event, ctx))
