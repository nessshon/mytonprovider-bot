from .update_providers import update_providers_job
from .update_telemetry import update_telemetry_job
from ....context import Context


async def sync_providers_job(ctx: Context) -> None:
    await update_providers_job(ctx)
    await update_telemetry_job(ctx)
