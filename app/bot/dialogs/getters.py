from aiogram_dialog import DialogManager

from ...database import UnitOfWork
from ...database.models import UserModel


async def main_menu(dialog_manager: DialogManager, **data):
    user_model: UserModel = dialog_manager.middleware_data["user_model"]
    enabled_alerts = user_model.alert_settings.enabled

    return {
        "user": dialog_manager.event.from_user,
        "user_model": user_model,
        "toggle_alerts": "enabled" if enabled_alerts else "disabled",
        "has_subscriptions": bool(user_model.subscriptions),
    }


async def provider_menu(dialog_manager: DialogManager, **kwargs):
    user = dialog_manager.middleware_data["user_model"]
    uow: UnitOfWork = dialog_manager.middleware_data["uow"]
    pubkey = dialog_manager.start_data.get("provider_pubkey")
    provider = await uow.provider.get(pubkey=pubkey)
    is_subscribed = await uow.subscription.exists(
        user_id=user.id, provider_pubkey=pubkey
    )
    print(provider)
    print(provider.telemetry)
    return {
        "is_subscribed": is_subscribed,
        "provider": provider,
        "telemetry": provider.telemetry,
    }


async def alert_settings_menu(dialog_manager: DialogManager, **kwargs):
    user_model: UserModel = dialog_manager.middleware_data["user_model"]

    return {"user_model": user_model}
