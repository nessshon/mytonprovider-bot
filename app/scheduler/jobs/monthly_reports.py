import logging

from ...alert.manager import AlertManager
from ...alert.repository import AlertRepository
from ...alert.types import AlertTypes, AlertStages
from ...context import Context
from ...database.metrics import build_monthly_report
from ...database.unitofwork import UnitOfWork

logger = logging.getLogger(__name__)


async def monthly_report_job(ctx: Context) -> None:
    alert_manager = AlertManager(ctx)

    async with UnitOfWork(ctx.db.session_factory) as uow:
        repo = AlertRepository(uow)
        providers = await uow.provider.all()
        users_by_provider = {}
        reports_by_provider = {}
        for provider in providers:
            reports_by_provider[provider.pubkey] = await build_monthly_report(
                uow.session, provider.pubkey
            )
            users_by_provider[provider.pubkey] = await repo.get_subscribed_users(
                provider.pubkey
            )

    for provider in providers:
        report = reports_by_provider[provider.pubkey]
        users = users_by_provider[provider.pubkey]
        for user in users:
            if AlertTypes.MONTHLY_REPORT in user.alert_settings.types:
                try:
                    await alert_manager.send_alert_message(
                        user=user,
                        alert_type=AlertTypes.MONTHLY_REPORT,
                        alert_stage=AlertStages.INFO,
                        provider=provider,
                        report=report,
                    )
                except (Exception,):
                    logger.warning(
                        "Failed to send monthly report to user %s",
                        user.user_id,
                    )
