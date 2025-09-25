from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button

from . import states
from ..utils.i18n import Localizer
from ...alert.thresholds import THRESHOLDS
from ...alert.types import AlertTypes
from ...context import Context
from ...database.models import UserModel
from ...database.unitofwork import UnitOfWork


async def change_provider_tab(
    _,
    __,
    manager: DialogManager,
    item_id: str,
) -> None:
    manager.start_data.update({"provider_tab": item_id})
    await manager.switch_to(manager.current_context().state)


async def unsubscribe(
    _,
    __,
    manager: DialogManager,
) -> None:
    user: UserModel = manager.middleware_data["user_model"]
    uow: UnitOfWork = manager.middleware_data["uow"]
    pubkey = manager.start_data.get("provider_pubkey")

    subscription = next(
        (s for s in user.subscriptions or [] if s.provider_pubkey == pubkey),
        None,
    )
    if subscription:
        user.subscriptions.remove(subscription)
        await uow.session.flush()

    manager.dialog_data["is_subscribed"] = False
    await manager.show()


async def subscribe(
    _,
    __,
    manager: DialogManager,
) -> None:
    manager.dialog_data.update(incorrect_password=False)


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


async def change_alert_tab(
    _,
    __,
    manager: DialogManager,
    item_id: str,
) -> None:
    manager.dialog_data["alert_tab"] = item_id
    await manager.switch_to(manager.current_context().state)


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


async def apply_thresholds(
    _,
    __,
    manager: DialogManager,
) -> None:
    await manager.show()


async def reset_thresholds(
    _,
    __,
    manager: DialogManager,
) -> None:
    await manager.show()


async def open_threshold_editor(
    _,
    button: Button,
    manager: DialogManager,
) -> None:
    user_model: UserModel = manager.middleware_data["user_model"]
    key = button.widget_id.removeprefix("threshold_")
    threshold_data = user_model.alert_settings.thresholds_data or THRESHOLDS
    current = threshold_data.get(key)

    manager.dialog_data.update(
        {
            "edit_threshold_key": key,
            "edit_threshold_value": int(current),
        }
    )
    await manager.next()


async def adjust_threshold(_, button, manager):
    uow: UnitOfWork = manager.middleware_data["uow"]
    user: UserModel = manager.middleware_data["user_model"]

    key = manager.dialog_data.get("edit_threshold_key")
    value = int(manager.dialog_data.get("edit_threshold_value", 0))

    raw = button.widget_id.removeprefix("step_")
    sign = -1 if raw.startswith("m") else 1
    step = int(raw[1:])

    new_value = max(30, min(100, value + sign * step))
    manager.dialog_data["edit_threshold_value"] = new_value

    data = dict(user.alert_settings.thresholds_data or {})
    data[key] = new_value
    user.alert_settings.thresholds_data = data

    await uow.session.flush()
    await manager.show()
