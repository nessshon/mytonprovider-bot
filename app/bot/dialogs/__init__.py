import logging

from aiogram import Dispatcher, Router
from aiogram_dialog import Dialog, LaunchMode

from . import windows

logger = logging.getLogger(__name__)


def register(dp: Dispatcher) -> None:
    dialog_router = Router()
    dialog_router.include_routers(
        Dialog(
            windows.main_menu,
            windows.main_not_found,
            windows.main_invalid_input,
            launch_mode=LaunchMode.ROOT,
        ),
        Dialog(
            windows.provider_menu,
            windows.provider_enter_password,
        ),
        Dialog(
            windows.allert_settings_menu,
            windows.alert_settings_set_threshold,
        ),
        Dialog(windows.stats_menu),
        Dialog(windows.language_menu),
        Dialog(windows.help_menu),
    )
    dp.include_router(dialog_router)

    logger.info("Dialogs registered")


__all__ = ["register"]
