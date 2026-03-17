import asyncio
import logging
import typing as t

from ...alert.manager import AlertManager
from ...alert.repository import AlertRepository
from ...alert.types import AlertTypes, AlertStages
from ...api.mytonprovider import ContractBagsRequest
from ...context import Context
from ...database.models import BagModel
from ...database.unitofwork import UnitOfWork

logger = logging.getLogger(__name__)

SYNC_BAGS_TIMEOUT = 4 * 60
MAX_DISPLAY_BAGS = 20


async def sync_bags_job(ctx: Context) -> None:
    try:
        await asyncio.wait_for(
            _sync_bags_impl(ctx),
            timeout=SYNC_BAGS_TIMEOUT,
        )
    except asyncio.TimeoutError:
        logger.error(
            "sync_bags_job timed out after %ss",
            SYNC_BAGS_TIMEOUT,
        )
    except (Exception,):
        logger.exception("sync_bags_job failed")
        raise


async def _sync_bags_impl(ctx: Context) -> None:
    async with UnitOfWork(ctx.db.session_factory) as uow:
        providers = await uow.provider.all()

    notifications: list[dict[str, t.Any]] = []

    for provider in providers:
        try:
            response = await ctx.mytonprovider.contracts.bags(
                ContractBagsRequest(provider=provider.pubkey)
            )
            new_bags = sorted(set(response.bags))
        except (Exception,):
            logger.warning(
                "Failed to fetch bags for provider %s",
                provider.pubkey,
            )
            continue

        async with UnitOfWork(ctx.db.session_factory) as uow:
            existing = await uow.bag.get(provider_pubkey=provider.pubkey)
            old_bags = sorted(existing.bags) if existing else None

            if old_bags is not None:
                added = sorted(set(new_bags) - set(old_bags))
                removed = sorted(set(old_bags) - set(new_bags))

                if added or removed:
                    notifications.append(
                        {
                            "provider": provider,
                            "added": added,
                            "removed": removed,
                        }
                    )

            bag_model = BagModel(
                provider_pubkey=provider.pubkey,
                bags=new_bags,
                bags_count=len(new_bags),
            )
            await uow.bag.upsert(bag_model)

    if not notifications:
        return

    alert_manager = AlertManager(ctx)

    async with UnitOfWork(ctx.db.session_factory) as uow:
        repo = AlertRepository(uow)
        users_by_provider = {}
        for n in notifications:
            pubkey = n["provider"].pubkey
            users_by_provider[pubkey] = await repo.get_subscribed_users(pubkey)

    for n in notifications:
        provider = n["provider"]
        added = n["added"]
        removed = n["removed"]
        users = users_by_provider.get(provider.pubkey, [])

        for user in users:
            enabled = {AlertTypes(a) for a in user.alert_settings.types or []}
            if AlertTypes.BAGS_CHANGED not in enabled:
                continue

            try:
                await alert_manager.send_alert_message(
                    user=user,
                    alert_type=AlertTypes.BAGS_CHANGED,
                    alert_stage=AlertStages.DETECTED,
                    provider=provider,
                    added_count=len(added),
                    removed_count=len(removed),
                    added_list=added[:MAX_DISPLAY_BAGS],
                    removed_list=removed[:MAX_DISPLAY_BAGS],
                )
            except (Exception,):
                logger.warning(
                    "Failed to send bags alert to user %s",
                    user.user_id,
                )
