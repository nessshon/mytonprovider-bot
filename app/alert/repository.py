from __future__ import annotations

import typing as t
from datetime import datetime

from aiogram.enums import ChatMemberStatus
from sqlalchemy import select
from sqlalchemy.orm import selectinload, aliased
from sqlalchemy.sql.expression import and_
from sqlalchemy.sql.functions import func

from .types import AlertTypes
from ..config import TIMEZONE
from ..database.models import (
    ProviderModel,
    TelemetryModel,
    TelemetryHistoryModel,
    UserModel,
    UserSubscriptionModel,
    UserTriggeredAlertModel,
)
from ..database.unitofwork import UnitOfWork


class AlertRepository:

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def get_providers_telemetry_with_prev_telemetry(
        self,
    ) -> list[tuple[ProviderModel, TelemetryModel, t.Optional[TelemetryHistoryModel]]]:
        t_alias = aliased(TelemetryModel)
        th_alias = aliased(TelemetryHistoryModel)

        prev_archived_at_sq = (
            select(func.max(TelemetryHistoryModel.archived_at))
            .where(
                TelemetryHistoryModel.provider_pubkey == t_alias.provider_pubkey,
                TelemetryHistoryModel.archived_at < t_alias.updated_at,
            )
            .correlate(t_alias)
            .scalar_subquery()
        )

        stmt = (
            select(ProviderModel, t_alias, th_alias)
            .join(
                t_alias, t_alias.provider_pubkey == ProviderModel.pubkey  # type: ignore[no-untyped-call]
            )
            .outerjoin(
                th_alias,
                and_(
                    th_alias.provider_pubkey == t_alias.provider_pubkey,
                    th_alias.archived_at == prev_archived_at_sq,
                ),
            )
        )

        async with self.uow:
            res = await self.uow.session.execute(stmt)

        return [
            (provider, telemetry, telemetry_history)
            for provider, telemetry, telemetry_history in res.all()
        ]

    async def get_subscribed_users(
        self,
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
        async with self.uow:
            result = await self.uow.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_active_alerts(
        self,
        user_id: int,
        provider_pubkey: str,
    ) -> t.Set[AlertTypes]:
        async with self.uow:
            result = await self.uow.user_triggered_alert.list(
                user_id=user_id,
                provider_pubkey=provider_pubkey,
            )
        return {AlertTypes(i.alert_type) for i in result}

    async def create_alert_record(
        self,
        user_id: int,
        alert_type: AlertTypes,
        provider_pubkey: str,
    ) -> None:
        async with self.uow:
            model = UserTriggeredAlertModel(
                user_id=user_id,
                provider_pubkey=provider_pubkey,
                alert_type=alert_type.value,
                triggered_at=datetime.now(TIMEZONE),
            )
            await self.uow.user_triggered_alert.create(model)

    async def delete_alert_record(
        self,
        user_id: int,
        alert_type: AlertTypes,
        provider_pubkey: str,
    ) -> None:
        async with self.uow:
            await self.uow.user_triggered_alert.delete(
                user_id=user_id,
                alert_type=alert_type.value,
                provider_pubkey=provider_pubkey,
            )

    async def exists_alert_record(
        self,
        user_id: int,
        alert_type: AlertTypes,
        provider_pubkey: str,
    ) -> bool:
        async with self.uow:
            return await self.uow.user_triggered_alert.exists(
                user_id=user_id,
                alert_type=alert_type.value,
                provider_pubkey=provider_pubkey,
            )
