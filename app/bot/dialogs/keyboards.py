from aiogram import F
from aiogram_dialog.widgets import kbd
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.text import Case, Multi, Const

from . import states, on_clicks
from ..widgets import I18NJinja
from ...config import SUPPORTED_LOCALES, ExternalLinks
from ...scheduler.user_alerts.types import UserAlertTypes

to_main = kbd.Start(
    id="back",
    text=I18NJinja("button.common.to_main"),
    state=states.MainMenu.MAIN,
)

main_menu = kbd.Group(
    kbd.SwitchInlineQueryCurrentChat(
        id="open_my_providers",
        text=I18NJinja("button.main_menu.my_providers"),
        switch_inline_query_current_chat=Const("my providers"),
        when=F["has_subscriptions"],
    ),
    kbd.SwitchInlineQueryCurrentChat(
        id="open_list_providers",
        text=I18NJinja("button.main_menu.list_providers"),
        switch_inline_query_current_chat=Const("list providers"),
    ),
    kbd.Button(
        id="toggle_alerts",
        text=Case(
            {
                True: I18NJinja("button.alert_state.enabled"),
                False: I18NJinja("button.alert_state.disabled"),
            },
            selector=F["user_model"].alert_settings.enabled,
        ),
        on_click=on_clicks.toggle_alerts,
    ),
    kbd.Start(
        id="to_alert_settings",
        text=I18NJinja("button.alert_settings.text"),
        state=states.AlertSettingsMenu.MAIN,
        when=F["user_model"].alert_settings.enabled,
    ),
    kbd.Row(
        kbd.Start(
            id="to_help_menu",
            text=I18NJinja("button.main_menu.help"),
            state=states.HelpMenu.MAIN,
        ),
        kbd.Start(
            id="to_language_menu",
            text=I18NJinja("button.main_menu.language"),
            state=states.LanguageMenu.MAIN,
        ),
    ),
)

provider_menu = kbd.Group(
    Button(
        id="toggle_subscription",
        text=Case(
            {
                True: I18NJinja("button.provider.unsubscribe"),
                False: I18NJinja("button.provider.subscribe"),
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
                        True: I18NJinja("button.alert_settings.state.enabled")
                        + I18NJinja(f"button.alert_settings.options.{opt.value}"),
                        False: I18NJinja("button.alert_settings.state.disabled")
                        + I18NJinja(f"button.alert_settings.options.{opt.value}"),
                    },
                    selector=F["user_model"].alert_settings.types.contains(opt.value),
                )
            ),
            on_click=on_clicks.toggle_alert_type,
        )
        for opt in UserAlertTypes
    ],
    kbd.Row(
        Button(
            id="enable_all_alerts",
            text=I18NJinja("button.alert_settings.enable_all"),
            on_click=on_clicks.toggle_alert_type,
        ),
        Button(
            id="disable_all_alerts",
            text=I18NJinja("button.alert_settings.disable_all"),
            on_click=on_clicks.toggle_alert_type,
        ),
    ),
    to_main,
)

language_menu = kbd.Group(
    kbd.Select(
        id="select_language",
        text=I18NJinja("language_name.{item}"),
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
        text=I18NJinja("button.help_menu.open_website"),
        url=Const(ExternalLinks.WEBSITE),
    ),
    kbd.Url(
        id="open_chat",
        text=I18NJinja("button.help_menu.open_chat"),
        url=Const(ExternalLinks.CHAT),
    ),
    kbd.Url(
        id="become_provider",
        text=I18NJinja("button.help_menu.become_provider"),
        url=Const(ExternalLinks.BECOME_PROVIDER),
    ),
    to_main,
)
