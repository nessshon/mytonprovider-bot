from aiogram_dialog import DialogManager
from sqlalchemy import select, func, and_

from app.database.metrics import (
    build_provider_wallet_metrics,
    build_provider_traffic_metrics,
    build_provider_storage_metrics,
    build_stats_summary,
    build_monthly_report,
)
from .consts import DEFAULT_PROVIDER_TAB, DEFAULT_ALERT_TAB
from ..utils.i18n import Localizer
from ...alert.thresholds import THRESHOLDS
from ...config import ADMIN_IDS
from ...database.models import ContractModel, UserModel
from ...database.unitofwork import UnitOfWork
from .widgets import BAGS_PER_PAGE, build_pagination_buttons


async def main_menu(
    dialog_manager: DialogManager,
    **_,
):
    user_model: UserModel = dialog_manager.middleware_data["user_model"]
    enabled_alerts = user_model.alert_settings.enabled
    uow: UnitOfWork = dialog_manager.middleware_data["uow"]

    list_providers_count = await uow.provider.count()
    my_providers_count = len(user_model.subscriptions)

    return {
        "user": dialog_manager.event.from_user,
        "user_model": user_model,
        "is_admin": user_model.user_id in ADMIN_IDS,
        "toggle_alerts": "enabled" if enabled_alerts else "disabled",
        "has_subscriptions": dialog_manager.middleware_data["has_subscriptions"],
        "list_providers_count": (
            f"[{list_providers_count}]" if list_providers_count > 0 else ""
        ),
        "my_providers_count": (
            f"[{my_providers_count}]" if my_providers_count > 0 else ""
        ),
    }


async def stats_menu(
    dialog_manager: DialogManager,
    **_,
):
    from ...context import get_context

    uow: UnitOfWork = dialog_manager.middleware_data["uow"]
    stats = await build_stats_summary(uow.session)

    ctx = get_context()
    started_at = getattr(ctx, "started_at", None)
    stats["bot_started_at"] = int(started_at) if started_at is not None else None

    return {"stats": stats}


async def provider_menu(
    dialog_manager: DialogManager,
    **_,
):
    provider_tab = dialog_manager.start_data.get("provider_tab", DEFAULT_PROVIDER_TAB)
    dialog_manager.current_context().widget_data["provider_tab"] = provider_tab

    user: UserModel = dialog_manager.middleware_data["user_model"]
    uow: UnitOfWork = dialog_manager.middleware_data["uow"]
    pubkey = dialog_manager.start_data.get("provider_pubkey")
    dialog_manager.dialog_data["provider_pubkey"] = pubkey

    provider = await uow.provider.get(pubkey=pubkey)
    telemetry = await uow.telemetry.get(provider_pubkey=pubkey)
    provider_wallet_metrics = await build_provider_wallet_metrics(uow.session, pubkey)
    provider_traffic_metrics = await build_provider_traffic_metrics(uow.session, pubkey)
    provider_storage_metrics = await build_provider_storage_metrics(uow.session, pubkey)
    provider_last_month_report = await build_monthly_report(uow.session, pubkey)
    provider_bags_count = await uow.contract.count(provider_pubkey=pubkey)

    subscription = next(
        (
            uta
            for uta in (user.subscriptions or [])
            if uta and uta.provider_pubkey == pubkey
        ),
        None,
    )
    is_subscribed = subscription is not None

    if telemetry and telemetry.telemetry_pass:
        user_pass_hash = subscription.telemetry_pass if subscription else "N/A"
        access_granted = user_pass_hash == telemetry.telemetry_pass
        password_invalid = is_subscribed and not access_granted
    else:
        if subscription and user.user_id in ADMIN_IDS:
            access_granted = True
        else:
            access_granted = False
        password_invalid = None

    return {
        "provider_tab": provider_tab,
        "is_subscribed": is_subscribed,
        "access_granted": access_granted,
        "password_invalid": password_invalid,
        "provider": provider,
        "telemetry": provider.telemetry_model,
        "provider_pubkey": pubkey,
        "provider_address": provider.address,
        "provider_wallet_metrics": provider_wallet_metrics,
        "provider_traffic_metrics": provider_traffic_metrics,
        "provider_storage_metrics": provider_storage_metrics,
        "provider_last_month_report": provider_last_month_report,
        "provider_bags_count": provider_bags_count,
    }


async def provider_enter_password(
    dialog_manager: DialogManager,
    **_,
):
    incorrect_password = dialog_manager.dialog_data.get("incorrect_password", False)
    return {"incorrect_password": incorrect_password}


async def provider_bags(
    dialog_manager: DialogManager,
    **_,
):
    uow: UnitOfWork = dialog_manager.middleware_data["uow"]
    pubkey = dialog_manager.dialog_data.get("provider_pubkey")
    bags_tab = dialog_manager.dialog_data.get("bags_tab", "all")
    bags_page = int(dialog_manager.dialog_data.get("bags_page", 0))

    dialog_manager.current_context().widget_data["bags_tab"] = bags_tab

    provider = await uow.provider.get(pubkey=pubkey)
    total_count = await uow.contract.count(provider_pubkey=pubkey)

    provider_filter = ContractModel.provider_pubkey == pubkey
    ok_filter = and_(provider_filter, ContractModel.reason == 0)
    problematic_filter = and_(
        provider_filter,
        ContractModel.reason.isnot(None),
        ContractModel.reason != 0,
    )

    result = await uow.session.execute(
        select(func.count()).select_from(ContractModel).where(ok_filter)
    )
    ok_count = result.scalar() or 0

    result = await uow.session.execute(
        select(func.count()).select_from(ContractModel).where(problematic_filter)
    )
    problematic_count = result.scalar() or 0

    if bags_tab == "problematic":
        tab_filter = problematic_filter
        total_filtered = problematic_count
    else:
        tab_filter = provider_filter
        total_filtered = total_count

    total_pages = max(1, (total_filtered + BAGS_PER_PAGE - 1) // BAGS_PER_PAGE)
    bags_page = min(bags_page, total_pages - 1)

    stmt = (
        select(ContractModel)
        .where(tab_filter)
        .order_by(ContractModel.reason_timestamp.desc().nulls_last())
        .offset(bags_page * BAGS_PER_PAGE)
        .limit(BAGS_PER_PAGE)
    )
    result = await uow.session.execute(stmt)
    page_contracts = list(result.scalars().all())

    page_keys = [
        {"address": c.address, "provider_pubkey": c.provider_pubkey}
        for c in page_contracts
    ]
    dialog_manager.dialog_data["page_keys"] = page_keys

    contract_items = [
        {
            "id": str(idx),
            "label": f"{c.bag_id[:10]} . . . {c.bag_id[-10:]}",
        }
        for idx, c in enumerate(page_contracts)
    ]

    pagination_items = build_pagination_buttons(bags_page, total_pages)

    return {
        "provider": provider,
        "bags_tab": bags_tab,
        "total_count": total_count,
        "ok_count": ok_count,
        "problematic_count": problematic_count,
        "contract_items": contract_items,
        "pagination_items": pagination_items,
    }


async def provider_bags_detail(
    dialog_manager: DialogManager,
    **_,
):
    uow: UnitOfWork = dialog_manager.middleware_data["uow"]
    contract_address = dialog_manager.dialog_data.get("contract_address")
    contract_pubkey = dialog_manager.dialog_data.get("contract_pubkey")

    contract = await uow.contract.get(
        address=contract_address,
        provider_pubkey=contract_pubkey,
    )
    if not contract:
        return {"contract": None}

    reason_descriptions = {
        0: "OK",
        101: "IP not found or unavailable",
        102: "IP not found or unavailable",
        103: "Connection timed out",
        201: "Offline or ports closed",
        202: "Storage contract issues",
        301: "No headers information",
        302: "No headers information",
        401: "Can't proof files availability",
        402: "Can't proof files availability",
        403: "Can't proof files availability",
    }
    reason_text = reason_descriptions.get(contract.reason, f"Unknown ({contract.reason})")

    return {
        "contract": contract,
        "reason_text": reason_text,
    }


async def alert_settings_menu(
    dialog_manager: DialogManager,
    **_,
):
    user_model: UserModel = dialog_manager.middleware_data["user_model"]

    alert_tab = dialog_manager.dialog_data.get("alert_tab", DEFAULT_ALERT_TAB)
    dialog_manager.current_context().widget_data["alert_tab"] = alert_tab
    thresholds_data = user_model.alert_settings.thresholds_data or THRESHOLDS

    return {
        "user_model": user_model,
        "alert_tab": alert_tab,
        "thresholds_data": thresholds_data,
    }


async def alert_settings_set_threshold(
    dialog_manager: DialogManager,
    localizer: Localizer,
    **_,
):
    user_model: UserModel = dialog_manager.middleware_data["user_model"]

    key = dialog_manager.dialog_data.get("edit_threshold_key")
    name = await localizer(f"buttons.alert_settings.types.options.{key}")
    value = int(dialog_manager.dialog_data.get("edit_threshold_value", 0))
    return {
        "user_model": user_model,
        "threshold_key": key,
        "threshold_name": name,
        "threshold_value": value,
    }
