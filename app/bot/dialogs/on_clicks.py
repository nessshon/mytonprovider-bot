from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets import kbd
from aiogram_dialog.widgets.kbd import Button

from . import states
from ...context import Context
from ...database import UnitOfWork
from ...database.models import UserModel, SubscriptionModel
from ...scheduler.user_alerts.types import UserAlertTypes
from ...utils.i18n import Localizer


async def toggle_subscription(
    _: CallbackQuery,
    __,
    manager: DialogManager,
):
    user = manager.middleware_data["user_model"]
    uow: UnitOfWork = manager.middleware_data["uow"]
    pubkey = manager.start_data.get("provider_pubkey")

    is_subscribed = await uow.subscription.exists(
        user_id=user.id, provider_pubkey=pubkey
    )

    if is_subscribed:
        await uow.subscription.delete(user_id=user.id, provider_pubkey=pubkey)
    else:
        await uow.subscription.create(
            SubscriptionModel(
                user_id=user.id,
                provider_pubkey=pubkey,
            )
        )

    manager.dialog_data["is_subscribed"] = not is_subscribed
    await manager.show()


async def toggle_alerts(
    _: CallbackQuery,
    __: Button,
    manager: DialogManager,
) -> None:
    uow: UnitOfWork = manager.middleware_data["uow"]
    user_model: UserModel = manager.middleware_data["user_model"]

    enabled = user_model.alert_settings.enabled
    user_model.alert_settings.enabled = not enabled

    await uow.session.flush()
    await manager.show()


async def toggle_alert_type(
    _: CallbackQuery,
    button: Button,
    manager: DialogManager,
) -> None:
    user_model: UserModel = manager.middleware_data["user_model"]
    uow: UnitOfWork = manager.middleware_data["uow"]

    widget_id = button.widget_id
    all_types = {e.value for e in UserAlertTypes}
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
    _: CallbackQuery,
    __: kbd.Select,
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
