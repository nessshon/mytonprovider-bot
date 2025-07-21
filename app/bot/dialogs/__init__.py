from aiogram import Dispatcher, Router
from aiogram_dialog import Dialog, LaunchMode

from . import windows


def register(dp: Dispatcher) -> None:
    router = Router()

    router.include_routers(
        Dialog(
            windows.main_menu,
            windows.main_not_found,
            windows.main_invalid_input,
            launch_mode=LaunchMode.ROOT,
        ),
        Dialog(windows.provider_menu),
        Dialog(windows.allert_settings_menu),
        Dialog(windows.language_menu),
        Dialog(windows.help_menu),
    )
    dp.include_router(router)


__all__ = ["register"]
