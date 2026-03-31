import asyncio
import logging

from ...alert.manager import AlertManager
from ...context import Context

logger = logging.getLogger(__name__)

ALERTS_DISPATCH_TIMEOUT = 55


async def alerts_dispatch_job(ctx: Context) -> None:
    try:
        await asyncio.wait_for(
            _alerts_dispatch_impl(ctx),
            timeout=ALERTS_DISPATCH_TIMEOUT,
        )
    except asyncio.TimeoutError:
        logger.error(
            "alerts_dispatch_job timed out after %ss",
            ALERTS_DISPATCH_TIMEOUT,
        )
    except Exception:
        logger.exception("alerts_dispatch_job failed")
        raise


async def _alerts_dispatch_impl(ctx: Context) -> None:
    alert_manager = AlertManager(ctx)
    await alert_manager.dispatch()
