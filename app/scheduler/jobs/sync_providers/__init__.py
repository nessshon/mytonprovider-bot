import asyncio
import logging

from .update_providers import update_providers_job
from .update_telemetry import update_telemetry_job
from ....context import Context

logger = logging.getLogger(__name__)

SYNC_PROVIDERS_TIMEOUT = 55


async def sync_providers_job(ctx: Context) -> None:
    try:
        await asyncio.wait_for(
            _sync_providers_impl(ctx),
            timeout=SYNC_PROVIDERS_TIMEOUT,
        )
    except asyncio.TimeoutError:
        logger.error(
            "sync_providers_job timed out after %ss",
            SYNC_PROVIDERS_TIMEOUT,
        )
    except Exception:
        logger.exception("sync_providers_job failed")
        raise


async def _sync_providers_impl(ctx: Context) -> None:
    await update_providers_job(ctx)
    await update_telemetry_job(ctx)
