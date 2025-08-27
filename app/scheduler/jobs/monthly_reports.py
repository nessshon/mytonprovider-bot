from datetime import date, timedelta, datetime

from ...config import TIMEZONE
from ...context import Context
from ...database import UnitOfWork
from ...database.models import ProviderModel
from ...utils.alerts.manager import AlertManager
from ...utils.alerts.types import MonthlyReport, AlertTypes, AlertStages


def prev_month_range(today: date) -> tuple[date, date, str]:
    first_of_this = today.replace(day=1)
    last_prev = first_of_this - timedelta(days=1)
    first_prev = last_prev.replace(day=1)
    return first_prev, last_prev, f"{first_prev:%Y-%m}"


async def aggregate_for_provider(
    uow: UnitOfWork,
    provider: ProviderModel,
) -> MonthlyReport:
    today = datetime.now(TIMEZONE).date()
    start_d, end_d, label = prev_month_range(today)

    used_sum_gb, total_gb_eom, used_gb_eom = await uow.sum_storage_used_between(
        provider.pubkey, start_d, end_d
    )

    telemetry = provider.telemetry
    if total_gb_eom is None and telemetry:
        total_gb_eom = float(telemetry.total_provider_space or 0.0)
    if used_gb_eom is None and telemetry:
        used_gb_eom = float(telemetry.used_provider_space or 0.0)

    used_space_bytes = int(used_sum_gb * 1_000_000_000)
    total_space_bytes = int((total_gb_eom or 0.0) * 1_000_000_000)
    used_space_eom_bytes = int((used_gb_eom or 0.0) * 1_000_000_000)

    earned = await uow.sum_wallet_earned_between(provider.pubkey, start_d, end_d)
    traffic_in, traffic_out = await uow.sum_traffic_between(
        provider.pubkey, start_d, end_d
    )

    return MonthlyReport(
        period=label,
        start_date=start_d,
        end_date=end_d,
        used_space_bytes=used_space_bytes,
        total_space_bytes=total_space_bytes,
        used_space_eom_bytes=used_space_eom_bytes,
        traffic_in_bytes=int(traffic_in or 0),
        traffic_out_bytes=int(traffic_out or 0),
        earned_nanoton=int(earned or 0),
        provider=provider,
    )


async def monthly_report_job(ctx: Context) -> None:
    uow = UnitOfWork(ctx.db.session_factory)
    alert_manager = AlertManager(ctx)

    async with uow:
        providers: list[ProviderModel] = await uow.provider.all()

    for provider in providers:
        async with uow:
            report = await aggregate_for_provider(uow, provider)

        users = await alert_manager.get_subscribed_users(uow, provider.pubkey)
        if not users:
            continue

        for user in users:
            if AlertTypes.MONTHLY_REPORT.value in user.alert_settings.types:
                await alert_manager.notify(
                    user=user,
                    alert_type=AlertTypes.MONTHLY_REPORT,
                    alert_stage=AlertStages.INFO,
                    report=report,
                )
