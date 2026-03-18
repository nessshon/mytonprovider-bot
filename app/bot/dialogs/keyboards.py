from aiogram import F
from aiogram.enums import ButtonStyle
from aiogram_dialog.widgets import kbd
from aiogram_dialog.widgets.style import Style
from aiogram_dialog.widgets.text import Case, Multi, Const, Format

from . import states, on_clicks
from .consts import PROVIDER_TABS, ALERT_TABS, STEP_LEFT, STEP_RIGHT, BAGS_TABS
from ..widgets import I18NJinja
from ...alert.types import AlertTypes
from ...config import SUPPORTED_LOCALES

to_main = kbd.Start(
    id="back",
    text=I18NJinja("buttons.common.to_main"),
    state=states.MainMenu.MAIN,
)

main_menu = kbd.Group(
    kbd.SwitchTo(
        id="search_provider",
        text=I18NJinja("buttons.main_menu.search_provider"),
        state=states.MainMenu.SEARCH_PROVIDER,
    ),
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
        style=Style(style=ButtonStyle.SUCCESS),
    ),
    kbd.Button(
        id="toggle_alerts_off",
        text=I18NJinja("buttons.alert_settings.state.enabled"),
        on_click=on_clicks.toggle_alerts,
        when=F["user_model"].alert_settings.enabled,
        style=Style(style=ButtonStyle.DANGER),
    ),
    kbd.Button(
        id="toggle_alerts_on",
        text=I18NJinja("buttons.alert_settings.state.disabled"),
        on_click=on_clicks.toggle_alerts,
        when=~F["user_model"].alert_settings.enabled,
        style=Style(style=ButtonStyle.SUCCESS),
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
    kbd.Start(
        id="to_stats",
        state=states.StatsMenu.MAIN,
        text=I18NJinja("buttons.common.stats"),
        when=F["is_admin"].is_(True),
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
            checked_style=Style(style=ButtonStyle.PRIMARY),
        ),
        width=3,
        when=F["access_granted"].is_(True),
    ),
    kbd.SwitchTo(
        id="update_password",
        text=I18NJinja("buttons.provider.update_password"),
        state=states.ProviderMenu.ENTER_PASSWORD,
        when=F["password_invalid"].is_(True),
        style=Style(style=ButtonStyle.SUCCESS),
    ),
    kbd.CopyText(
        text=I18NJinja("buttons.provider.copy_pubkey"),
        copy_text=Format("{provider_pubkey}"),
    ),
    kbd.CopyText(
        text=I18NJinja("buttons.provider.copy_address"),
        copy_text=Format("{provider_address}"),
    ),
    kbd.SwitchTo(
        id="open_bags",
        text=I18NJinja("buttons.provider.bags"),
        state=states.ProviderMenu.BAGS,
        when=F["access_granted"].is_(True),
    ),
    kbd.Button(
        id="unsubscribe",
        text=I18NJinja("buttons.provider.unsubscribe"),
        on_click=on_clicks.unsubscribe,
        when=F["is_subscribed"].is_(True),
        style=Style(style=ButtonStyle.DANGER),
    ),
    kbd.Next(
        id="subscribe",
        text=I18NJinja("buttons.provider.subscribe"),
        when=F["is_subscribed"].is_(False),
        on_click=on_clicks.subscribe,
        style=Style(style=ButtonStyle.SUCCESS),
    ),
    to_main,
)

provider_bags_menu = kbd.Group(
    kbd.Group(
        kbd.Radio(
            checked_text=Const("• ") + I18NJinja("buttons.provider.bags_tab.{item}"),
            unchecked_text=I18NJinja("buttons.provider.bags_tab.{item}"),
            id="bags_tab",
            item_id_getter=lambda x: x,
            items=BAGS_TABS,
            on_click=on_clicks.change_bags_tab,
            checked_style=Style(style=ButtonStyle.PRIMARY),
        ),
        width=2,
    ),
    kbd.Column(
        kbd.Select(
            Format("{item[label]}"),
            id="select_contract",
            item_id_getter=lambda item: item["id"],
            items="contract_items",
            on_click=on_clicks.open_contract_detail,
        ),
    ),
    kbd.Group(
        kbd.Select(
            Format("{item[label]}"),
            id="select_page",
            item_id_getter=lambda item: item["id"],
            items="pagination_items",
            on_click=on_clicks.change_bags_page,
        ),
        width=5,
    ),
    kbd.SwitchTo(
        id="bags_back",
        text=I18NJinja("buttons.common.to_main"),
        state=states.ProviderMenu.MAIN,
    ),
)

provider_bags_detail_menu = kbd.Group(
    kbd.CopyText(
        text=I18NJinja("buttons.provider.bags_detail.copy_bag_id"),
        copy_text=Format("{contract.bag_id}"),
    ),
    kbd.Url(
        id="open_bag",
        text=I18NJinja("buttons.provider.bags_detail.open_bag"),
        url=Format("https://mytonstorage.org/api/v1/gateway/{contract.bag_id}"),
    ),
    kbd.Url(
        id="open_contract",
        text=I18NJinja("buttons.provider.bags_detail.open_contract"),
        url=Format("https://tonviewer.com/{contract.address}"),
    ),
    kbd.Url(
        id="open_owner",
        text=I18NJinja("buttons.provider.bags_detail.open_owner"),
        url=Format("https://tonviewer.com/{contract.owner_address}"),
    ),
    kbd.SwitchTo(
        id="back_to_bags",
        text=I18NJinja("buttons.common.to_main"),
        state=states.ProviderMenu.BAGS,
    ),
)

alert_settings_menu = kbd.Group(
    kbd.Group(
        kbd.Radio(
            checked_text=Const("• ") + I18NJinja("buttons.alert_settings.tab.{item}"),
            unchecked_text=I18NJinja("buttons.alert_settings.tab.{item}"),
            id="alert_tab",
            item_id_getter=lambda x: x,
            items=ALERT_TABS,
            on_click=on_clicks.change_alert_tab,
            checked_style=Style(style=ButtonStyle.PRIMARY),
        ),
        width=3,
    ),
    kbd.Group(
        *[
            kbd.Button(
                id=f"toggle_alert_{opt.value}",
                text=Multi(
                    Case(
                        {
                            True: I18NJinja(
                                "buttons.alert_settings.types.state.enabled"
                            )
                            + I18NJinja(
                                f"buttons.alert_settings.types.options.{opt.value}"
                            ),
                            False: I18NJinja(
                                "buttons.alert_settings.types.state.disabled"
                            )
                            + I18NJinja(
                                f"buttons.alert_settings.types.options.{opt.value}"
                            ),
                        },
                        selector=F["user_model"].alert_settings.types.contains(
                            opt.value
                        ),
                    )
                ),
                on_click=on_clicks.toggle_alert_type,
            )
            for opt in AlertTypes
        ],
        kbd.Row(
            kbd.Button(
                id="enable_all_alerts",
                text=I18NJinja("buttons.alert_settings.types.enable_all"),
                on_click=on_clicks.toggle_alert_type,
                style=Style(style=ButtonStyle.SUCCESS),
            ),
            kbd.Button(
                id="disable_all_alerts",
                text=I18NJinja("buttons.alert_settings.types.disable_all"),
                on_click=on_clicks.toggle_alert_type,
                style=Style(style=ButtonStyle.DANGER),
            ),
        ),
        when=F["alert_tab"].contains("types"),
    ),
    kbd.Group(
        kbd.Button(
            id="threshold_cpu_high",
            text=I18NJinja("buttons.alert_settings.thresholds.cpu_high"),
            on_click=on_clicks.open_threshold_editor,
        ),
        kbd.Button(
            id="threshold_ram_high",
            text=I18NJinja("buttons.alert_settings.thresholds.ram_high"),
            on_click=on_clicks.open_threshold_editor,
        ),
        kbd.Button(
            id="threshold_network_high",
            text=I18NJinja("buttons.alert_settings.thresholds.network_high"),
            on_click=on_clicks.open_threshold_editor,
        ),
        kbd.Button(
            id="threshold_disk_load_high",
            text=I18NJinja("buttons.alert_settings.thresholds.disk_load_high"),
            on_click=on_clicks.open_threshold_editor,
        ),
        kbd.Button(
            id="threshold_disk_space_low",
            text=I18NJinja("buttons.alert_settings.thresholds.disk_space_low"),
            on_click=on_clicks.open_threshold_editor,
        ),
        when=F["alert_tab"].contains("thresholds"),
    ),
    to_main,
)

alert_settings_set_threshold = kbd.Group(
    kbd.Row(
        *[
            kbd.Button(
                id=f"step_{sid}",
                text=Const(label),
                on_click=on_clicks.adjust_threshold,
                style=Style(style=ButtonStyle.DANGER),
            )
            for sid, label in STEP_LEFT
        ],
        kbd.Button(
            id="current_value",
            text=Format("{threshold_value}"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        *[
            kbd.Button(
                id=f"step_{sid}",
                text=Const(label),
                on_click=on_clicks.adjust_threshold,
                style=Style(style=ButtonStyle.SUCCESS),
            )
            for sid, label in STEP_RIGHT
        ],
    ),
    kbd.Back(text=I18NJinja("buttons.common.to_main")),
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
