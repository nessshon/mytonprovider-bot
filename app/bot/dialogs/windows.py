from aiogram import F
from aiogram_dialog import Window
from aiogram_dialog.widgets import kbd
from aiogram_dialog.widgets.text import Case

from . import getters
from . import keyboards
from . import states
from .consts import PROVIDER_TABS
from ..widgets import I18NJinja

main_menu = Window(
    I18NJinja("messages.main.menu"),
    keyboards.main_menu,
    getter=getters.main_menu,
    state=states.MainMenu.MAIN,
)

main_not_found = Window(
    I18NJinja("messages.main.not_found"),
    keyboards.to_main,
    state=states.MainMenu.NOT_FOUND,
)

main_invalid_input = Window(
    I18NJinja("messages.main.invalid_input"),
    keyboards.to_main,
    state=states.MainMenu.INVALID_INPUT,
)

stats_menu = Window(
    I18NJinja("messages.stats.menu"),
    keyboards.to_main,
    getter=getters.stats_menu,
    state=states.StatsMenu.MAIN,
)

allert_settings_menu = Window(
    I18NJinja(
        "messages.alert_settings.types_menu",
        when=F["alert_tab"].contains("types"),
    ),
    I18NJinja(
        "messages.alert_settings.thresholds_menu",
        when=F["alert_tab"].contains("thresholds"),
    ),
    keyboards.alert_settings_menu,
    getter=getters.alert_settings_menu,
    state=states.AlertSettingsMenu.MAIN,
)

alert_settings_set_threshold = Window(
    I18NJinja("messages.alert_settings.edit_threshold.title"),
    I18NJinja("messages.alert_settings.edit_threshold.hint"),
    keyboards.alert_settings_set_threshold,
    getter=getters.alert_settings_set_threshold,
    state=states.AlertSettingsMenu.SET_THRESHOLD,
)

provider_menu = Window(
    I18NJinja("messages.provider.menu"),
    Case(
        {i: I18NJinja(f"messages.provider.{i}") for i in PROVIDER_TABS},
        selector="provider_tab",
        when=F["access_granted"].is_(True),
    ),
    I18NJinja(
        "messages.provider.password_invalid",
        when=F["password_invalid"].is_(True),
    ),
    keyboards.provider_menu,
    getter=getters.provider_menu,
    state=states.ProviderMenu.MAIN,
)

provider_enter_password = Window(
    I18NJinja(
        "messages.provider.enter_password",
        when=F["incorrect_password"].is_(False),
    ),
    I18NJinja(
        "messages.provider.incorrect_password",
        when=F["incorrect_password"].is_(True),
    ),
    kbd.Back(I18NJinja("buttons.common.to_main")),
    getter=getters.provider_enter_password,
    state=states.ProviderMenu.ENTER_PASSWORD,
)


language_menu = Window(
    I18NJinja("messages.language.menu"),
    keyboards.language_menu,
    state=states.LanguageMenu.MAIN,
)

help_menu = Window(
    I18NJinja("messages.help.menu"),
    keyboards.help_menu,
    state=states.HelpMenu.MAIN,
)
