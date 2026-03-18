import asyncio
import logging
import typing as t
from collections import defaultdict

from ...alert.manager import AlertManager
from ...alert.repository import AlertRepository
from ...alert.types import AlertTypes, AlertStages
from ...api.mytonprovider import ContractBagsRequest, ContractInfo
from ...context import Context
from ...database.models import ContractModel
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


async def _fetch_all_contracts(ctx: Context) -> t.Optional[list[ContractInfo]]:
    all_contracts: list[ContractInfo] = []
    offset = 0
    limit = 500
    max_retries = 3
    expected_total = None

    while True:
        response = None
        for attempt in range(max_retries):
            try:
                response = await ctx.mytonprovider.contracts.bags(
                    ContractBagsRequest(limit=limit, offset=offset)
                )
                break
            except (Exception,):
                logger.warning(
                    "Failed to fetch contracts at offset %d (attempt %d/%d)",
                    offset, attempt + 1, max_retries,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)

        if response is None:
            return None

        if expected_total is None:
            expected_total = response.total
        elif response.total != expected_total:
            logger.warning(
                "Total changed during fetch: expected %d, got %d. Restarting.",
                expected_total, response.total,
            )
            return None

        all_contracts.extend(response.contracts)
        if len(all_contracts) >= response.total:
            break
        offset += limit
        await asyncio.sleep(1)

    if len(all_contracts) != expected_total:
        logger.warning(
            "Fetched %d contracts but expected %d. Skipping update.",
            len(all_contracts), expected_total,
        )
        return None

    return all_contracts


async def _sync_bags_impl(ctx: Context) -> None:
    new_contracts = await _fetch_all_contracts(ctx)
    if new_contracts is None:
        return

    new_by_key = {(c.address, c.provider_pubkey): c for c in new_contracts}
    new_keys = set(new_by_key.keys())

    async with UnitOfWork(ctx.db.session_factory) as uow:
        existing = await uow.contract.all()

    old_by_key = {(c.address, c.provider_pubkey): c for c in existing}
    old_keys = set(old_by_key.keys())

    if not new_keys and old_keys:
        logger.debug(
            "Skipping contracts update: API returned empty, had %d contracts",
            len(old_keys),
        )
        return

    is_first_run = not old_keys and new_keys
    added_keys = new_keys - old_keys
    removed_keys = old_keys - new_keys
    common_keys = new_keys & old_keys

    async with UnitOfWork(ctx.db.session_factory) as uow:
        for key in removed_keys:
            await uow.contract.delete(address=key[0], provider_pubkey=key[1])

        for key in added_keys:
            c = new_by_key[key]
            await uow.contract.create(ContractModel(
                address=c.address,
                provider_pubkey=c.provider_pubkey,
                bag_id=c.bag_id,
                owner_address=c.owner_address,
                size=c.size,
                reason=c.reason,
                reason_timestamp=c.reason_timestamp,
            ))

        for key in common_keys:
            c = new_by_key[key]
            old = old_by_key[key]
            if (c.reason != old.reason
                    or c.size != old.size
                    or c.owner_address != old.owner_address):
                db_obj = await uow.contract.get(address=key[0], provider_pubkey=key[1])
                if db_obj:
                    db_obj.reason = c.reason
                    db_obj.reason_timestamp = c.reason_timestamp
                    db_obj.size = c.size
                    db_obj.owner_address = c.owner_address

    if is_first_run:
        logger.info("First run: inserted %d contracts, skipping notifications", len(added_keys))
        return

    added_by_provider: dict[str, list[str]] = defaultdict(list)
    for key in added_keys:
        added_by_provider[new_by_key[key].provider_pubkey].append(new_by_key[key].bag_id)

    removed_by_provider: dict[str, list[str]] = defaultdict(list)
    for key in removed_keys:
        removed_by_provider[old_by_key[key].provider_pubkey].append(old_by_key[key].bag_id)

    notifications: dict[str, dict[str, list[str]]] = {}
    all_pubkeys = set(added_by_provider.keys()) | set(removed_by_provider.keys())
    for pubkey in all_pubkeys:
        added = sorted(added_by_provider.get(pubkey, []))
        removed = sorted(removed_by_provider.get(pubkey, []))
        if added or removed:
            notifications[pubkey] = {"added": added, "removed": removed}

    if not notifications:
        return

    alert_manager = AlertManager(ctx)

    async with UnitOfWork(ctx.db.session_factory) as uow:
        providers_map = {p.pubkey: p for p in await uow.provider.all()}
        repo = AlertRepository(uow)
        users_by_provider = {}
        for pubkey in notifications:
            users_by_provider[pubkey] = await repo.get_subscribed_users(pubkey)

    for pubkey, diff in notifications.items():
        provider = providers_map.get(pubkey)
        if not provider:
            continue
        added = diff["added"]
        removed = diff["removed"]
        users = users_by_provider.get(pubkey, [])

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
