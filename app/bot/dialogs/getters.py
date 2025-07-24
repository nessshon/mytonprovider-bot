from aiogram_dialog import DialogManager

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
    user = dialog_manager.middleware_data["user_model"]
    uow: UnitOfWork = dialog_manager.middleware_data["uow"]
    pubkey = dialog_manager.start_data.get("provider_pubkey")
    provider = await uow.provider.get(pubkey=pubkey)
    is_subscribed = await uow.user_subscription.exists(
        user_id=user.id, provider_pubkey=pubkey
    )

    return {
        "is_subscribed": is_subscribed,
        "provider": provider,
        "telemetry": provider.telemetry,
        "provider_pubkey": pubkey,
        "provider_address": provider.address,
    }


async def alert_settings_menu(dialog_manager: DialogManager, **_):
    user_model: UserModel = dialog_manager.middleware_data["user_model"]

    return {"user_model": user_model}
