import logging
import typing as t
from datetime import datetime

from aiogram.enums import ChatMemberStatus
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .overload_detector import OverloadDetector
from .types import AlertTypes
from ..i18n import Localizer
from ...config import TIMEZONE
from ...context import Context
from ...database import UnitOfWork
from ...database.models import (
    UserModel,
    TelemetryModel,
    ProviderModel,
    UserSubscriptionModel,
    UserTriggeredAlertModel,
)


class AlertManager:

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx

    async def _process_user_alerts(
            self,
            uow: UnitOfWork,
            user: UserModel,
            triggered_alerts: t.Set[AlertTypes],
            provider: ProviderModel,
            telemetry: TelemetryModel,
    ) -> None:
        active_alerts = await self._get_user_active_alerts(uow, user.user_id)

        new_alerts = triggered_alerts - active_alerts
        resolved_alerts = active_alerts - triggered_alerts

        for alert_type in new_alerts:
            if alert_type not in user.alert_settings.types:
                continue

            await self.notify(
                user=user,
                alert_type=alert_type,
                provider=provider,
                telemetry=telemetry,
            )

            await self._create_alert_record(
                uow, user.user_id, alert_type, provider.pubkey
            )

        for alert_type in resolved_alerts:
            await self._delete_alert_record(
                uow, user.user_id, alert_type, provider.pubkey
            )

    async def dispatch(
            self,
            provider: ProviderModel,
            telemetry: TelemetryModel,
    ) -> None:
        uow = UnitOfWork(self.ctx.db.session_factory)

        async with uow:
            overload_detecotor = OverloadDetector(provider, telemetry)
            triggered_alerts = overload_detecotor.get_triggered_alerts()
            if not triggered_alerts:
                return

            logging.info(
                f"Triggered alerts for provider {provider.pubkey}: {triggered_alerts}"
            )
            for user in await self._get_subscribed_users(uow, provider.pubkey):
                if not user.alert_settings or not user.alert_settings.enabled:
                    continue

                await self._process_user_alerts(
                    uow=uow,
                    user=user,
                    triggered_alerts=triggered_alerts,
                    provider=provider,
                    telemetry=telemetry,
                )

    async def notify(
            self,
            user: UserModel,
            alert_type: AlertTypes,
            **kwargs: t.Any,
    ) -> None:
        localizer = Localizer(
            self.ctx.i18n.jinja_env,
            self.ctx.i18n.locales_data[user.language_code],
        )

        text = await localizer(f"alerts.{alert_type}.text", **kwargs)
        button = await localizer("buttons.common.hide", **kwargs)

        inline_keyboard = [[InlineKeyboardButton(text=button, callback_data="hide")]]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

        await self.ctx.broadcaster.send_message(user.user_id, text, reply_markup)

    @staticmethod
    async def _get_subscribed_users(
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
            .options(
                selectinload(UserModel.alert_settings),
            )
        )
        result = await uow.session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def _get_user_active_alerts(
            uow: UnitOfWork,
            user_id: int,
    ) -> t.Set[AlertTypes]:
        result = await uow.user_triggered_alert.list(user_id=user_id)
        return {AlertTypes(i.alert_type) for i in result}

    @staticmethod
    async def _create_alert_record(
            uow: UnitOfWork,
            user_id: int,
            alert_type: AlertTypes,
            provider_pubkey: str,
    ) -> None:
        model = UserTriggeredAlertModel(
            user_id=user_id,
            provider_pubkey=provider_pubkey,
            alert_type=alert_type,
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
        await uow.user_triggered_alert.delete(
            user_id=user_id,
            alert_type=alert_type,
            provider_pubkey=provider_pubkey,
        )
