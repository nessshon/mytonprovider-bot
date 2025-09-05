from __future__ import annotations

import asyncio
import logging
import typing as t
from datetime import datetime

from aiogram.enums import ChatMemberStatus
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .detector import OverloadDetector, ServiceRestartedDetector
from .types import AlertTypes, AlertStages
from ..i18n import Localizer
from ...config import (
    TIMEZONE,
    SUPPORTED_LOCALES,
    DEFAULT_LOCALE,
)
from ...context import Context
from ...database.models import (
    UserModel,
    TelemetryModel,
    ProviderModel,
    UserSubscriptionModel,
    UserTriggeredAlertModel,
)
from ...database.unitofwork import UnitOfWork

logger = logging.getLogger(__name__)


class AlertManager:

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx

    async def _process_user_alerts(
        self,
        uow: UnitOfWork,
        user: UserModel,
        triggered_alerts: list[tuple[AlertTypes, dict]],
        provider: ProviderModel,
        telemetry: t.Optional[TelemetryModel] = None,
    ) -> None:
        user_id = user.user_id
        pubkey = provider.pubkey

        active_alerts = await self._get_user_active_alerts(uow, user_id, pubkey)
        triggered_alert_types = {a[0] for a in triggered_alerts}

        new_alerts = [
            (ta, extra) for ta, extra in triggered_alerts if ta not in active_alerts
        ]
        resolved_alerts = [
            (ta, {}) for ta in active_alerts if ta not in triggered_alert_types
        ]

        for alert_type, extra in new_alerts:
            await self.notify(
                user=user,
                alert_type=alert_type,
                alert_stage=AlertStages.DETECTED,
                provider=provider,
                telemetry=telemetry,
                **extra,
            )
            if alert_type != AlertTypes.SERVICE_RESTARTED:
                await self._create_alert_record(uow, user_id, alert_type, pubkey)

        for alert_type, extra in resolved_alerts:
            if await self._exists_alert_record(uow, user_id, alert_type, pubkey):
                await self.notify(
                    user=user,
                    alert_type=alert_type,
                    alert_stage=AlertStages.RESOLVED,
                    provider=provider,
                    telemetry=telemetry,
                    **extra,
                )
                await self._delete_alert_record(uow, user_id, alert_type, pubkey)

    async def dispatch(
        self,
        provider: ProviderModel,
        curr_telemetry: t.Optional[TelemetryModel] = None,
        prev_telemetry: t.Optional[TelemetryModel] = None,
    ) -> None:
        uow = UnitOfWork(self.ctx.db.session_factory)
        users = await self.get_subscribed_users(uow, provider.pubkey)
        if not users:
            return

        for user in users:
            triggered_alerts: list[tuple[AlertTypes, dict]] = []
            user_enabled_alerts = user.alert_settings.types or []

            overload_detector = OverloadDetector(
                provider=provider,
                telemetry=curr_telemetry,
                thresholds=user.alert_settings.thresholds_data,
            )
            for alert_type in overload_detector.get_triggered_alerts():
                if alert_type.value in user_enabled_alerts:
                    triggered_alerts.append((alert_type, {}))

            if prev_telemetry and AlertTypes.SERVICE_RESTARTED in user_enabled_alerts:
                restart_detector = ServiceRestartedDetector()
                triggered_alerts.extend(
                    restart_detector.get_triggered_alerts(
                        prev_telemetry, curr_telemetry
                    )
                )

            await self._process_user_alerts(
                uow, user, triggered_alerts, provider, curr_telemetry
            )

    async def notify(
        self,
        user: UserModel,
        alert_type: AlertTypes,
        alert_stage: AlertStages,
        **kwargs: t.Any,
    ) -> None:
        try:
            language_code = (
                user.language_code
                if user.language_code in SUPPORTED_LOCALES
                else DEFAULT_LOCALE
            )
            localizer = Localizer(
                self.ctx.i18n.jinja_env,
                self.ctx.i18n.locales_data[language_code],
            )
            text = await localizer(f"alerts.{alert_type}.{alert_stage}", **kwargs)
            button = await localizer("buttons.common.hide", **kwargs)

            inline_keyboard = [
                [InlineKeyboardButton(text=button, callback_data="hide")]
            ]
            reply_markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

            await self.ctx.broadcaster.send_message(user.user_id, text, reply_markup)
        except Exception as e:
            logger.error(
                "Failed to notify user %s for alert '%s': %s",
                user.user_id,
                alert_type.name,
                e,
            )
        await asyncio.sleep(0.025)

    @staticmethod
    async def get_subscribed_users(
        uow: UnitOfWork,
        provider_pubkey: str,
    ) -> t.List[UserModel]:
        stmt = (
            select(UserModel)
            .join(UserModel.subscriptions)
            .join(UserModel.alert_settings)
            .where(
                UserModel.state == ChatMemberStatus.MEMBER,
                UserModel.alert_settings.has(enabled=True),
                UserSubscriptionModel.provider_pubkey == provider_pubkey,
            )
            .options(selectinload(UserModel.alert_settings))
        )
        async with uow:
            result = await uow.session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def _get_user_active_alerts(
        uow: UnitOfWork,
        user_id: int,
        provider_pubkey: str,
    ) -> t.Set[AlertTypes]:
        async with uow:
            result = await uow.user_triggered_alert.list(
                user_id=user_id,
                provider_pubkey=provider_pubkey,
            )
        return {AlertTypes(i.alert_type) for i in result}

    @staticmethod
    async def _create_alert_record(
        uow: UnitOfWork,
        user_id: int,
        alert_type: AlertTypes,
        provider_pubkey: str,
    ) -> None:
        async with uow:
            model = UserTriggeredAlertModel(
                user_id=user_id,
                provider_pubkey=provider_pubkey,
                alert_type=alert_type.value,
                triggered_at=datetime.now(TIMEZONE),
            )
            await uow.user_triggered_alert.create(model)

    @staticmethod
    async def _delete_alert_record(
        uow: UnitOfWork,
        user_id: int,
        alert_type: AlertTypes,
        provider_pubkey: str,
    ) -> None:
        async with uow:
            await uow.user_triggered_alert.delete(
                user_id=user_id,
                alert_type=alert_type.value,
                provider_pubkey=provider_pubkey,
            )

    @staticmethod
    async def _exists_alert_record(
        uow: UnitOfWork,
        user_id: int,
        alert_type: AlertTypes,
        provider_pubkey: str,
    ) -> bool:
        async with uow:
            return await uow.user_triggered_alert.exists(
                user_id=user_id,
                alert_type=alert_type.value,
                provider_pubkey=provider_pubkey,
            )
