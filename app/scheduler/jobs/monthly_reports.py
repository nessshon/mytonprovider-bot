from ...alert.manager import AlertManager
from ...alert.types import AlertTypes, AlertStages
from ...context import Context
from ...database.metrics import build_monthly_report
from ...database.unitofwork import UnitOfWork


async def monthly_report_job(ctx: Context) -> None:
    uow = UnitOfWork(ctx.db.session_factory)
    alert_manager = AlertManager(ctx)

    async with uow:
        providers = await uow.provider.all()

    for provider in providers:
        async with uow:
            report = await build_monthly_report(uow.session, provider.pubkey)

        users = await alert_manager.repo.get_subscribed_users(provider.pubkey)
        for user in users:
            if AlertTypes.MONTHLY_REPORT in user.alert_settings.types:
                await alert_manager.send_alert_message(
                    user=user,
                    alert_type=AlertTypes.MONTHLY_REPORT,
                    alert_stage=AlertStages.INFO,
                    provider=provider,
                    report=report,
                )
