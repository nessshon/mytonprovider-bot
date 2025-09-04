from aiogram.fsm.state import StatesGroup, State


class MainMenu(StatesGroup):
    MAIN = State()
    NOT_FOUND = State()
    INVALID_INPUT = State()


class StatsMenu(StatesGroup):
    MAIN = State()


class LanguageMenu(StatesGroup):
    MAIN = State()


class AlertSettingsMenu(StatesGroup):
    MAIN = State()
    SET_THRESHOLD = State()


class HelpMenu(StatesGroup):
    MAIN = State()


class ProviderMenu(StatesGroup):
    MAIN = State()
    ENTER_PASSWORD = State()
