import typing as t

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from .detector import AlertDetector
from .repository import AlertRepository
from .types import AlertTypes, AlertStages
from ..bot.utils.i18n import Localizer
from ..context import Context
from ..database.models import (
    UserModel,
    ProviderModel,
    TelemetryModel,
    TelemetryHistoryModel,
)
from ..database.unitofwork import UnitOfWork


class AlertManager:

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx
        self.broadcaster = ctx.broadcaster
        self.uow = UnitOfWork(ctx.db.session_factory)
        self.repo = AlertRepository(self.uow)

    async def dispatch(self) -> None:
        payload = await self.repo.get_providers_telemetry_with_prev_telemetry()
        for provider, telemetry, telemetry_history in payload:
            users = await self.repo.get_subscribed_users(provider.pubkey)
            for user in users:
                payload = (user, provider, telemetry, telemetry_history)
                await self.process_user_service_alerts(*payload)
                await self.process_user_base_alerts(*payload)

    async def process_user_service_alerts(
        self,
        user: UserModel,
        provider: ProviderModel,
        telemetry: TelemetryModel,
        telemetry_history: TelemetryHistoryModel,
    ) -> None:
        alert_detector = AlertDetector(
            provider=provider,
            telemetry=telemetry,
            telemetry_history=telemetry_history,
            user_thresholds=user.alert_settings.thresholds_data or {},
        )
        triggered = alert_detector.get_triggered_service_alerts()
        enabled = {AlertTypes(a) for a in user.alert_settings.types or []}

        for alert_type, payload in triggered:
            if alert_type not in enabled:
                continue
            await self.send_alert_message(
                user=user,
                alert_type=alert_type,
                alert_stage=AlertStages.DETECTED,
                provider=provider,
                telemetry=telemetry,
                **payload,
            )

    async def process_user_base_alerts(
        self,
        user: UserModel,
        provider: ProviderModel,
        telemetry: TelemetryModel,
        telemetry_history: TelemetryHistoryModel,
    ) -> None:
        user_id = user.user_id
        alert_detector = AlertDetector(
            provider=provider,
            telemetry=telemetry,
            telemetry_history=telemetry_history,
            user_thresholds=user.alert_settings.thresholds_data or {},
        )
        triggered = alert_detector.get_triggered_base_alerts()
        enabled = {AlertTypes(a) for a in user.alert_settings.types or []}
        active = await self.repo.get_user_active_alerts(user_id, provider.pubkey)

        detected, resolved = alert_detector.diff_alerts(triggered, enabled, active)
        detected_payload = (detected, AlertStages.DETECTED, provider, telemetry, user)
        resolved_payload = (resolved, AlertStages.RESOLVED, provider, telemetry, user)

        await self.apply_base_alerts(*detected_payload)
        await self.apply_base_alerts(*resolved_payload)

    async def apply_base_alerts(
        self,
        alerts: t.Set[AlertTypes],
        alert_stage: AlertStages,
        provider: ProviderModel,
        telemetry: TelemetryModel,
        user: UserModel,
    ) -> None:
        user_id, pubkey = user.user_id, provider.pubkey
        for alert_type in alerts:
            await self.send_alert_message(
                user=user,
                alert_type=alert_type,
                alert_stage=alert_stage,
                provider=provider,
                telemetry=telemetry,
            )
            if alert_stage == AlertStages.DETECTED:
                await self.repo.create_alert_record(user_id, alert_type, pubkey)
            else:
                await self.repo.delete_alert_record(user_id, alert_type, pubkey)

    async def send_alert_message(
        self,
        user: UserModel,
        alert_type: AlertTypes,
        alert_stage: AlertStages,
        **kwargs: t.Any,
    ) -> None:
        localizer = Localizer(
            self.ctx.i18n.jinja_env,
            self.ctx.i18n.locales_data[user.language_code],
        )
        text = await localizer(f"alerts.{alert_type}.{alert_stage}", **kwargs)
        button = await localizer("buttons.common.hide", **kwargs)

        inline_keyboard = [[InlineKeyboardButton(text=button, callback_data="hide")]]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
        await self.ctx.broadcaster.send_message(user.user_id, text, reply_markup)
