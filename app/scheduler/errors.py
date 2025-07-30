import asyncio
import logging

from aiogram.types import BufferedInputFile
from aiogram.utils.markdown import hbold, hcode
from apscheduler.events import JobExecutionEvent

from ..bot import Broadcaster
from ..config import DEV_ID
from ..context import Context, get_context

logger = logging.getLogger(__name__)


async def _on_job_error(event: JobExecutionEvent, ctx: Context) -> None:
    logger.exception("Unhandled error in scheduler job")

    broadcaster: Broadcaster = ctx.broadcaster
    exc = event.exception
    exc_type = type(exc).__name__
    exc_text = str(exc).strip().split("\n")[0]
    caption = f"{hbold(exc_type)}: {hcode(exc_text[:900])}"

    traceback_text = event.traceback or "No traceback available"
    filename = f"error_{event.job_id or 'unknown'}.txt"
    document = BufferedInputFile(traceback_text.encode(), filename=filename)

    await broadcaster.send_document(DEV_ID, document, caption=caption)


def on_job_error(event: JobExecutionEvent) -> None:
    ctx: Context = get_context()
    loop = asyncio.get_event_loop()
    loop.create_task(_on_job_error(event, ctx))
