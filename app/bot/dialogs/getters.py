from datetime import datetime

from aiogram_dialog import DialogManager

from .consts import DEFAULT_PROVIDER_TAB
from ...config import TIMEZONE
from ...database import UnitOfWork
from ...database.models import UserModel


async def main_menu(dialog_manager: DialogManager, **_):
    user_model: UserModel = dialog_manager.middleware_data["user_model"]
    enabled_alerts = user_model.alert_settings.enabled
    uow: UnitOfWork = dialog_manager.middleware_data["uow"]

    list_providers_count = await uow.provider.count()
    my_providers_count = await uow.user_subscription.count()

    return {
        "user": dialog_manager.event.from_user,
        "user_model": user_model,
        "toggle_alerts": "enabled" if enabled_alerts else "disabled",
        "has_subscriptions": dialog_manager.middleware_data["has_subscriptions"],
        "list_providers_count": (
            f"[{list_providers_count}]" if list_providers_count > 0 else ""
        ),
        "my_providers_count": (
            f"[{my_providers_count}]" if my_providers_count > 0 else ""
        ),
    }


async def provider_menu(dialog_manager: DialogManager, **_):
    provider_tab = dialog_manager.start_data.get("provider_tab", DEFAULT_PROVIDER_TAB)
    dialog_manager.current_context().widget_data["provider_tab"] = provider_tab

    user = dialog_manager.middleware_data["user_model"]
    uow: UnitOfWork = dialog_manager.middleware_data["uow"]
    pubkey = dialog_manager.start_data.get("provider_pubkey")
    today = datetime.now(TIMEZONE).date()

    provider = await uow.provider.get(pubkey=pubkey)
    is_subscribed = await uow.user_subscription.exists(
        user_id=user.id, provider_pubkey=pubkey
    )
    provider_wallet_metrics = await uow.get_provider_wallet_metrics(
        pubkey=pubkey,
        today=today,
    )

    return {
        "provider_tab": provider_tab,
        "is_subscribed": is_subscribed,
        "provider": provider,
        "telemetry": provider.telemetry,
        "provider_pubkey": pubkey,
        "provider_address": provider.address,
        "provider_wallet_metrics": provider_wallet_metrics,
    }


async def alert_settings_menu(dialog_manager: DialogManager, **_):
    user_model: UserModel = dialog_manager.middleware_data["user_model"]

    return {"user_model": user_model}
