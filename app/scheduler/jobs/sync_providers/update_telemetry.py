import logging

from sqlalchemy.sql.expression import delete

from ....context import Context
from ....database.helpers import now_rounded_min
from ....database.models import TelemetryModel, TelemetryHistoryModel
from ....database.unitofwork import UnitOfWork

logger = logging.getLogger(__name__)


async def update_telemetry_job(ctx: Context) -> None:
    uow = UnitOfWork(ctx.db.session_factory)
    now = now_rounded_min()

    response = await ctx.mytonprovider.telemetry()

    telemetry_models = []
    telemetry_history_models = []
    for telemetry in response.providers:
        data = telemetry.model_dump()
        data["provider_pubkey"] = telemetry.storage.provider.pubkey.lower()

        telemetry_data = data.copy()
        telemetry_history_data = data.copy()

        telemetry_data["updated_at"] = now
        telemetry_models.append(TelemetryModel(**telemetry_data))

        telemetry_history_data["archived_at"] = now
        telemetry_history_models.append(TelemetryHistoryModel(**data))

    async with uow:
        await uow.telemetry_history.bulk_upsert(telemetry_history_models)
        await uow.telemetry.bulk_upsert(telemetry_models)

        current_pubkeys = tuple({m.provider_pubkey for m in telemetry_models})
        if current_pubkeys:
            stmt = delete(TelemetryModel).where(
                ~TelemetryModel.provider_pubkey.in_(current_pubkeys)
            )
            await uow.session.execute(stmt)
