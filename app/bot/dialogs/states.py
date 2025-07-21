from aiogram.fsm.state import StatesGroup, State


class MainMenu(StatesGroup):
    MAIN = State()
    NOT_FOUND = State()
    INVALID_INPUT = State()


class LanguageMenu(StatesGroup):
    MAIN = State()


class AlertSettingsMenu(StatesGroup):
    MAIN = State()


class HelpMenu(StatesGroup):
    MAIN = State()


class ProviderMenu(StatesGroup):
    MAIN = State()
