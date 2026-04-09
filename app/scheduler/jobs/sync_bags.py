import asyncio
import logging
import typing as t
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ...alert.manager import AlertManager
from ...alert.repository import AlertRepository
from ...alert.types import AlertTypes, AlertStages
from ...api.mytonprovider import ContractBagsRequest, ContractInfo
from ...config import TIMEZONE
from ...context import Context
from ...database.models import ContractModel
from ...database.unitofwork import UnitOfWork

logger = logging.getLogger(__name__)

SYNC_BAGS_TIMEOUT = 4 * 60
MAX_DISPLAY_BAGS = 20
MISSING_THRESHOLD = timedelta(days=3)
REASON_THRESHOLD = timedelta(hours=24)

ContractKey = tuple[str, str]


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TIMEZONE)
    return dt


@dataclass
class ContractDiff:
    truly_new: set[ContractKey] = field(default_factory=set)
    returned: set[ContractKey] = field(default_factory=set)
    newly_missing: set[ContractKey] = field(default_factory=set)
    confirmed_missing: set[ContractKey] = field(default_factory=set)
    still_present: set[ContractKey] = field(default_factory=set)


def _compute_diff(
    old_by_key: dict[ContractKey, ContractModel],
    new_keys: set[ContractKey],
    now: datetime,
) -> ContractDiff:
    old_keys = set(old_by_key.keys())
    returned = {
        k for k in (new_keys & old_keys) if old_by_key[k].missing_since is not None
    }
    return ContractDiff(
        truly_new=new_keys - old_keys,
        returned=returned,
        newly_missing={
            k for k in (old_keys - new_keys) if old_by_key[k].missing_since is None
        },
        confirmed_missing={
            k
            for k in (old_keys - new_keys)
            if old_by_key[k].missing_since is not None
            and (now - _ensure_aware(old_by_key[k].missing_since)) > MISSING_THRESHOLD
        },
        still_present=(new_keys & old_keys) - returned,
    )


def _build_notifications(
    diff: ContractDiff,
    old_by_key: dict[ContractKey, ContractModel],
    new_by_key: dict[ContractKey, ContractInfo],
) -> dict[str, dict[str, list[str]]]:
    added_by_provider: dict[str, list[str]] = defaultdict(list)
    for key in diff.truly_new:
        added_by_provider[new_by_key[key].provider_pubkey].append(
            new_by_key[key].bag_id
        )

    removed_by_provider: dict[str, list[str]] = defaultdict(list)
    for key in diff.confirmed_missing:
        removed_by_provider[old_by_key[key].provider_pubkey].append(
            old_by_key[key].bag_id
        )

    notifications: dict[str, dict[str, list[str]]] = {}
    all_pubkeys = (
        set(added_by_provider.keys())
        | set(removed_by_provider.keys())
    )
    for pubkey in all_pubkeys:
        added = sorted(added_by_provider.get(pubkey, []))
        removed = sorted(removed_by_provider.get(pubkey, []))
        if added or removed:
            notifications[pubkey] = {
                "added": added,
                "removed": removed,
                "failed": [],
                "recovered": [],
            }

    return notifications


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
                    offset,
                    attempt + 1,
                    max_retries,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)

        if response is None:
            return None

        if expected_total is None:
            expected_total = response.total
        elif response.total != expected_total:
            logger.warning(
                "Total changed during fetch: expected %d, got %d. Skipping.",
                expected_total,
                response.total,
            )
            return None

        all_contracts.extend(response.contracts)
        if len(all_contracts) >= response.total:
            break
        offset += limit
        await asyncio.sleep(1)

    if len(all_contracts) != expected_total:
        logger.warning(
            "Fetched %d contracts but expected %d. Skipping.",
            len(all_contracts),
            expected_total,
        )
        return None

    return all_contracts


async def _apply_db_changes(
    ctx: Context,
    diff: ContractDiff,
    old_by_key: dict[ContractKey, ContractModel],
    new_by_key: dict[ContractKey, ContractInfo],
    now: datetime,
) -> tuple[set[ContractKey], set[ContractKey]]:
    reason_failed: set[ContractKey] = set()
    reason_recovered: set[ContractKey] = set()

    async with UnitOfWork(ctx.db.session_factory) as uow:
        for key in diff.truly_new:
            c = new_by_key[key]
            await uow.contract.create(
                ContractModel(
                    address=c.address,
                    provider_pubkey=c.provider_pubkey,
                    bag_id=c.bag_id,
                    owner_address=c.owner_address,
                    size=c.size,
                    reason=c.reason,
                    reason_timestamp=c.reason_timestamp,
                )
            )

        for key in diff.returned:
            db_obj = await uow.contract.get(address=key[0], provider_pubkey=key[1])
            if db_obj:
                missing_min = int(
                    (now - _ensure_aware(db_obj.missing_since)).total_seconds() / 60
                )
                logger.info(
                    "Contract %s returned after %dm missing (provider %s)",
                    db_obj.bag_id[:16],
                    missing_min,
                    key[1][:8],
                )
                c = new_by_key[key]
                db_obj.missing_since = None
                db_obj.reason = c.reason
                db_obj.reason_timestamp = c.reason_timestamp
                db_obj.previous_reason = None
                db_obj.reason_changed_at = None
                db_obj.size = c.size
                db_obj.owner_address = c.owner_address

        if diff.newly_missing:
            logger.info("Marking %d contracts as missing", len(diff.newly_missing))
        for key in diff.newly_missing:
            db_obj = await uow.contract.get(address=key[0], provider_pubkey=key[1])
            if db_obj:
                db_obj.missing_since = now

        if diff.confirmed_missing:
            logger.info(
                "Deleting %d contracts missing for >%s",
                len(diff.confirmed_missing),
                MISSING_THRESHOLD,
            )
        for key in diff.confirmed_missing:
            await uow.contract.delete(address=key[0], provider_pubkey=key[1])

        for key in diff.still_present:
            c = new_by_key[key]
            old = old_by_key[key]
            db_obj = None

            if old.reason_changed_at is not None:
                if c.reason == old.previous_reason:
                    db_obj = await uow.contract.get(
                        address=key[0], provider_pubkey=key[1]
                    )
                    if db_obj:
                        db_obj.reason = c.reason
                        db_obj.reason_timestamp = c.reason_timestamp
                        db_obj.previous_reason = None
                        db_obj.reason_changed_at = None
                        logger.debug(
                            "Contract %s reason reverted to %s, debounce cancelled",
                            old.bag_id[:16],
                            c.reason,
                        )
                elif (now - _ensure_aware(old.reason_changed_at)) > REASON_THRESHOLD:
                    db_obj = await uow.contract.get(
                        address=key[0], provider_pubkey=key[1]
                    )
                    if db_obj:
                        db_obj.reason = c.reason
                        db_obj.reason_timestamp = c.reason_timestamp
                        prev = old.previous_reason
                        db_obj.previous_reason = None
                        db_obj.reason_changed_at = None
                        if (prev is None or prev == 0) and c.reason and c.reason != 0:
                            reason_failed.add(key)
                        elif prev and prev != 0 and (not c.reason or c.reason == 0):
                            reason_recovered.add(key)
                        logger.info(
                            "Contract %s reason confirmed: %s -> %s (provider %s)",
                            old.bag_id[:16],
                            prev,
                            c.reason,
                            key[1][:8],
                        )
                elif c.reason != old.reason:
                    db_obj = await uow.contract.get(
                        address=key[0], provider_pubkey=key[1]
                    )
                    if db_obj:
                        db_obj.reason = c.reason
                        db_obj.reason_timestamp = c.reason_timestamp
            elif c.reason != old.reason:
                db_obj = await uow.contract.get(address=key[0], provider_pubkey=key[1])
                if db_obj:
                    db_obj.previous_reason = old.reason
                    db_obj.reason_changed_at = now
                    db_obj.reason = c.reason
                    db_obj.reason_timestamp = c.reason_timestamp
                    logger.debug(
                        "Contract %s reason changed %s -> %s, debounce started",
                        old.bag_id[:16],
                        old.reason,
                        c.reason,
                    )

            if c.size != old.size or c.owner_address != old.owner_address:
                if db_obj is None:
                    db_obj = await uow.contract.get(
                        address=key[0], provider_pubkey=key[1]
                    )
                if db_obj:
                    db_obj.size = c.size
                    db_obj.owner_address = c.owner_address

    if reason_failed or reason_recovered:
        logger.info(
            "Reason debounce confirmed: %d failed, %d recovered",
            len(reason_failed),
            len(reason_recovered),
        )

    return reason_failed, reason_recovered


async def _send_notifications(
    ctx: Context,
    notifications: dict[str, dict[str, list[str]]],
) -> None:
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

            if added or removed:
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


async def _sync_bags_impl(ctx: Context) -> None:
    new_contracts = await _fetch_all_contracts(ctx)
    if new_contracts is None:
        return

    new_by_key = {(c.address, c.provider_pubkey): c for c in new_contracts}
    new_keys = set(new_by_key.keys())

    async with UnitOfWork(ctx.db.session_factory) as uow:
        existing = await uow.contract.all()

    old_by_key = {(c.address, c.provider_pubkey): c for c in existing}
    active_keys = {k for k, c in old_by_key.items() if c.missing_since is None}

    if not new_keys and active_keys:
        logger.debug(
            "Skipping contracts update: API returned empty, had %d active contracts",
            len(active_keys),
        )
        return

    is_first_run = not old_by_key and new_keys
    now = datetime.now(TIMEZONE)

    diff = _compute_diff(old_by_key, new_keys, now)
    await _apply_db_changes(
        ctx,
        diff,
        old_by_key,
        new_by_key,
        now,
    )

    if is_first_run:
        logger.info(
            "First run: inserted %d contracts, skipping notifications",
            len(diff.truly_new),
        )
        return

    notifications = _build_notifications(
        diff,
        old_by_key,
        new_by_key,
    )
    if notifications:
        await _send_notifications(ctx, notifications)
