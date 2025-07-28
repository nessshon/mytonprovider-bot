from aiogram import F
from aiogram_dialog.widgets import kbd
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.text import Case, Multi, Const, Format

from . import states, on_clicks
from .consts import PROVIDER_TABS
from ..widgets import I18NJinja
from ...config import SUPPORTED_LOCALES
from ...utils.alerts.types import AlertTypes

to_main = kbd.Start(
    id="back",
    text=I18NJinja("buttons.common.to_main"),
    state=states.MainMenu.MAIN,
)

main_menu = kbd.Group(
    kbd.SwitchInlineQueryCurrentChat(
        id="open_my_providers",
        text=I18NJinja("buttons.main_menu.my_providers"),
        switch_inline_query_current_chat=Const("my providers"),
        when=F["has_subscriptions"],
    ),
    kbd.SwitchInlineQueryCurrentChat(
        id="open_list_providers",
        text=I18NJinja("buttons.main_menu.list_providers"),
        switch_inline_query_current_chat=Const("list providers"),
    ),
    kbd.Start(
        id="to_alert_settings",
        text=I18NJinja("buttons.alert_settings.text"),
        state=states.AlertSettingsMenu.MAIN,
        when=F["user_model"].alert_settings.enabled,
    ),
    kbd.Button(
        id="toggle_alerts",
        text=Case(
            {
                True: I18NJinja("buttons.alert_state.enabled"),
                False: I18NJinja("buttons.alert_state.disabled"),
            },
            selector=F["user_model"].alert_settings.enabled,
        ),
        on_click=on_clicks.toggle_alerts,
    ),
    kbd.Row(
        kbd.Start(
            id="to_help_menu",
            text=I18NJinja("buttons.main_menu.help"),
            state=states.HelpMenu.MAIN,
        ),
        kbd.Start(
            id="to_language_menu",
            text=I18NJinja("buttons.main_menu.language"),
            state=states.LanguageMenu.MAIN,
        ),
    ),
)

provider_menu = kbd.Group(
    kbd.Group(
        kbd.Radio(
            checked_text=Const("• ") + I18NJinja("buttons.provider.tab.{item}"),
            unchecked_text=I18NJinja("buttons.provider.tab.{item}"),
            id="provider_tab",
            item_id_getter=lambda x: x,
            items=PROVIDER_TABS,
            on_click=on_clicks.change_provider_tab,
        ),
        width=3,
    ),
    kbd.CopyText(
        text=I18NJinja("buttons.provider.copy_pubkey"),
        copy_text=Format("{provider_pubkey}"),
    ),
    kbd.CopyText(
        text=I18NJinja("buttons.provider.copy_address"),
        copy_text=Format("{provider_address}"),
    ),
    Button(
        id="toggle_subscription",
        text=Case(
            {
                True: I18NJinja("buttons.provider.unsubscribe"),
                False: I18NJinja("buttons.provider.subscribe"),
            },
            selector=F["is_subscribed"],
        ),
        on_click=on_clicks.toggle_subscription,
    ),
    to_main,
)

alert_settings_menu = kbd.Group(
    *[
        Button(
            id=f"toggle_alert_{opt.value}",
            text=Multi(
                Case(
                    {
                        True: I18NJinja("buttons.alert_settings.state.enabled")
                        + I18NJinja(f"buttons.alert_settings.options.{opt.value}"),
                        False: I18NJinja("buttons.alert_settings.state.disabled")
                        + I18NJinja(f"buttons.alert_settings.options.{opt.value}"),
                    },
                    selector=F["user_model"].alert_settings.types.contains(opt.value),
                )
            ),
            on_click=on_clicks.toggle_alert_type,
        )
        for opt in AlertTypes
    ],
    kbd.Row(
        Button(
            id="enable_all_alerts",
            text=I18NJinja("buttons.alert_settings.enable_all"),
            on_click=on_clicks.toggle_alert_type,
        ),
        Button(
            id="disable_all_alerts",
            text=I18NJinja("buttons.alert_settings.disable_all"),
            on_click=on_clicks.toggle_alert_type,
        ),
    ),
    to_main,
)

language_menu = kbd.Group(
    kbd.Select(
        id="select_language",
        text=I18NJinja("language_names.{item}"),
        item_id_getter=lambda x: x,
        items=SUPPORTED_LOCALES,
        on_click=on_clicks.select_language,
    ),
    to_main,
    width=1,
)

help_menu = kbd.Group(
    kbd.Url(
        id="open_website",
        text=I18NJinja("buttons.help_menu.open_website.text"),
        url=I18NJinja("buttons.help_menu.open_website.url"),
    ),
    kbd.Url(
        id="open_chat",
        text=I18NJinja("buttons.help_menu.open_chat.text"),
        url=I18NJinja("buttons.help_menu.open_chat.url"),
    ),
    kbd.Url(
        id="become_provider",
        text=I18NJinja("buttons.help_menu.become_provider.text"),
        url=I18NJinja("buttons.help_menu.become_provider.url"),
    ),
    to_main,
)
