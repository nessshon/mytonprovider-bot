from aiogram_dialog import DialogManager

from app.database.metrics import (
    build_provider_wallet_metrics,
    build_provider_traffic_metrics,
    build_provider_storage_metrics,
    build_stats_summary,
)
from .consts import DEFAULT_PROVIDER_TAB, DEFAULT_ALERT_TAB
from ..utils.i18n import Localizer
from ...alert.thresholds import THRESHOLDS
from ...config import ADMIN_IDS
from ...database.models import UserModel
from ...database.unitofwork import UnitOfWork


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
    uow: UnitOfWork = dialog_manager.middleware_data["uow"]
    stats = await build_stats_summary(uow.session)
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
    }


async def provider_enter_password(
    dialog_manager: DialogManager,
    **_,
):
    incorrect_password = dialog_manager.dialog_data.get("incorrect_password", False)
    return {"incorrect_password": incorrect_password}


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
