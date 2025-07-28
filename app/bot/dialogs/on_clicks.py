from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button

from . import states
from ...context import Context
from ...database import UnitOfWork
from ...database.models import (
    UserModel,
    UserSubscriptionModel,
)
from ...utils.alerts.types import AlertTypes
from ...utils.i18n import Localizer


async def change_provider_tab(
    _,
    __,
    manager: DialogManager,
    item_id: str,
) -> None:
    manager.start_data.update({"provider_tab": item_id})
    await manager.switch_to(manager.current_context().state)


async def toggle_subscription(
    _,
    __,
    manager: DialogManager,
) -> None:
    user = manager.middleware_data["user_model"]
    uow: UnitOfWork = manager.middleware_data["uow"]
    pubkey = manager.start_data.get("provider_pubkey")

    is_subscribed = await uow.user_subscription.exists(
        user_id=user.id, provider_pubkey=pubkey
    )
    if is_subscribed:
        await uow.user_subscription.delete(user_id=user.id, provider_pubkey=pubkey)
    else:
        await uow.user_subscription.create(
            UserSubscriptionModel(
                user_id=user.id,
                provider_pubkey=pubkey,
            )
        )

    manager.dialog_data["is_subscribed"] = not is_subscribed
    await manager.show()


async def toggle_alerts(
    _,
    __,
    manager: DialogManager,
) -> None:
    uow: UnitOfWork = manager.middleware_data["uow"]
    user_model: UserModel = manager.middleware_data["user_model"]

    enabled = user_model.alert_settings.enabled
    user_model.alert_settings.enabled = not enabled

    await uow.session.flush()
    await manager.show()


async def toggle_alert_type(
    _,
    button: Button,
    manager: DialogManager,
) -> None:
    user_model: UserModel = manager.middleware_data["user_model"]
    uow: UnitOfWork = manager.middleware_data["uow"]

    widget_id, all_types = button.widget_id, {e.value for e in AlertTypes}
    current_types = set(user_model.alert_settings.types or [])

    if widget_id == "enable_all_alerts":
        user_model.alert_settings.types = list(all_types)
    elif widget_id == "disable_all_alerts":
        user_model.alert_settings.types = []
    else:
        alert_type = widget_id.removeprefix("toggle_alert_")
        if alert_type in current_types:
            current_types.remove(alert_type)
        else:
            current_types.add(alert_type)
        user_model.alert_settings.types = list(current_types)

    await uow.session.flush()
    await manager.show()


async def select_language(
    _,
    __,
    manager: DialogManager,
    item_id: str,
) -> None:
    ctx: Context = manager.middleware_data["ctx"]
    uow: UnitOfWork = manager.middleware_data["uow"]
    user_model = manager.middleware_data["user_model"]

    user_model.language_code = item_id
    locale_data = ctx.i18n.locales_data.get(item_id)
    manager.middleware_data["localizer"] = Localizer(
        jinja_env=ctx.i18n.jinja_env,
        locale_data=locale_data,
    )

    await uow.session.flush()
    await manager.start(states.MainMenu.MAIN)
