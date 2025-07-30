import logging

from aiogram.types import ErrorEvent
from aiogram_dialog import DialogManager, StartMode, ShowMode

from ..dialogs import states

logger = logging.getLogger(__name__)


async def on_unknown_intent(event: ErrorEvent, dialog_manager: DialogManager):
    logger.error(f"Restarting dialog: {event.exception}")
    await dialog_manager.start(
        states.MainMenu.MAIN,
        mode=StartMode.RESET_STACK,
        show_mode=ShowMode.DELETE_AND_SEND,
    )


async def on_unknown_state(event: ErrorEvent, dialog_manager: DialogManager):
    logger.error(f"Restarting dialog: {event.exception}")
    await dialog_manager.start(
        states.MainMenu.MAIN,
        mode=StartMode.RESET_STACK,
        show_mode=ShowMode.DELETE_AND_SEND,
    )
