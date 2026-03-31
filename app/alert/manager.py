import logging
import typing as t
from dataclasses import dataclass, field

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

logger = logging.getLogger(__name__)


@dataclass
class PendingAlertAction:
    user_id: int
    alert_type: AlertTypes
    provider_pubkey: str
    stage: AlertStages


@dataclass
class DispatchContext:
    entries: list = field(default_factory=list)
    users_by_provider: dict = field(default_factory=dict)
    active_alerts: dict = field(default_factory=dict)
    pending_actions: list[PendingAlertAction] = field(default_factory=list)


class AlertManager:

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx
        self.broadcaster = ctx.broadcaster

    async def dispatch(self) -> None:
        dc = DispatchContext()

        async with UnitOfWork(self.ctx.db.session_factory) as uow:
            repo = AlertRepository(uow)
            dc.entries = await repo.get_providers_telemetry_with_prev_telemetry()
            for provider, telemetry, telemetry_history in dc.entries:
                users = await repo.get_subscribed_users(provider.pubkey)
                dc.users_by_provider[provider.pubkey] = users
                for user in users:
                    key = (user.user_id, provider.pubkey)
                    dc.active_alerts[key] = await repo.get_user_active_alerts(
                        user.user_id, provider.pubkey
                    )

        for provider, telemetry, telemetry_history in dc.entries:
            users = dc.users_by_provider[provider.pubkey]
            for user in users:
                await self._process_user_alerts(
                    dc, user, provider, telemetry, telemetry_history
                )

        if dc.pending_actions:
            async with UnitOfWork(self.ctx.db.session_factory) as uow:
                repo = AlertRepository(uow)
                for action in dc.pending_actions:
                    if action.stage == AlertStages.DETECTED:
                        await repo.create_alert_record(
                            action.user_id, action.alert_type, action.provider_pubkey
                        )
                    else:
                        await repo.delete_alert_record(
                            action.user_id, action.alert_type, action.provider_pubkey
                        )

    async def _process_user_alerts(
        self,
        dc: DispatchContext,
        user: UserModel,
        provider: ProviderModel,
        telemetry: TelemetryModel,
        telemetry_history: TelemetryHistoryModel,
    ) -> None:
        bot_started_at = getattr(self.ctx, "started_at", None)
        alert_detector = AlertDetector(
            provider=provider,
            telemetry=telemetry,
            telemetry_history=telemetry_history,
            user_thresholds=user.alert_settings.thresholds_data or {},
            bot_started_at=bot_started_at,
        )
        enabled = {AlertTypes(a) for a in user.alert_settings.types or []}

        triggered_service = alert_detector.get_triggered_service_alerts()
        for alert_type, alert_payload in triggered_service:
            if alert_type not in enabled:
                continue
            try:
                await self.send_alert_message(
                    user=user,
                    alert_type=alert_type,
                    alert_stage=AlertStages.DETECTED,
                    provider=provider,
                    telemetry=telemetry,
                    **alert_payload,
                )
            except (Exception,):
                logger.warning(
                    "Failed to send service alert %s to user %s",
                    alert_type, user.user_id,
                )

        triggered_base = alert_detector.get_triggered_base_alerts()
        key = (user.user_id, provider.pubkey)
        active = dc.active_alerts.get(key, set())
        detected, resolved = alert_detector.diff_alerts(triggered_base, enabled, active)

        for alert_type in detected:
            try:
                await self.send_alert_message(
                    user=user,
                    alert_type=alert_type,
                    alert_stage=AlertStages.DETECTED,
                    provider=provider,
                    telemetry=telemetry,
                )
            except (Exception,):
                logger.warning(
                    "Failed to send alert %s to user %s",
                    alert_type, user.user_id,
                )
            dc.pending_actions.append(PendingAlertAction(
                user_id=user.user_id,
                alert_type=alert_type,
                provider_pubkey=provider.pubkey,
                stage=AlertStages.DETECTED,
            ))

        for alert_type in resolved:
            try:
                await self.send_alert_message(
                    user=user,
                    alert_type=alert_type,
                    alert_stage=AlertStages.RESOLVED,
                    provider=provider,
                    telemetry=telemetry,
                )
            except (Exception,):
                logger.warning(
                    "Failed to send resolve alert %s to user %s",
                    alert_type, user.user_id,
                )
            dc.pending_actions.append(PendingAlertAction(
                user_id=user.user_id,
                alert_type=alert_type,
                provider_pubkey=provider.pubkey,
                stage=AlertStages.RESOLVED,
            ))

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
