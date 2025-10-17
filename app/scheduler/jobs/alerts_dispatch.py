import logging

from ...alert.manager import AlertManager
from ...context import Context

logger = logging.getLogger(__name__)


async def alerts_dispatch_job(ctx: Context) -> None:
    alert_manager = AlertManager(ctx)
    await alert_manager.dispatch()
