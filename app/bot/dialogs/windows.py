from aiogram_dialog import Window
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

allert_settings_menu = Window(
    I18NJinja("messages.alert_settings.menu"),
    keyboards.alert_settings_menu,
    getter=getters.alert_settings_menu,
    state=states.AlertSettingsMenu.MAIN,
)

provider_menu = Window(
    I18NJinja("messages.provider.menu"),
    Case(
        {i: I18NJinja(f"messages.provider.{i}") for i in PROVIDER_TABS},
        selector="provider_tab",
    ),
    keyboards.provider_menu,
    getter=getters.provider_menu,
    state=states.ProviderMenu.MAIN,
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
