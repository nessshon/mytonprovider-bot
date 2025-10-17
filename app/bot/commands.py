import logging
import typing as t

from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import BotCommand, BotCommandScopeDefault

from .utils.i18n import Localizer
from .utils.i18n.utils import LOCALE_TO_TELEGRAM
from ..config import SUPPORTED_LOCALES, DEFAULT_LOCALE
from ..context import Context

logger = logging.getLogger(__name__)


async def build_commands(localizer: Localizer) -> t.List[BotCommand]:
    commands_section = localizer.locale_data.get("commands", {})
    result: t.List[BotCommand] = []

    for name, entry in commands_section.items():
        if not isinstance(entry, dict):
            continue

        key = f"commands.{name}.description"
        try:
            description = await localizer(key)
        except KeyError:
            continue

        result.append(BotCommand(command=name, description=description))

    return result


async def setup(ctx: Context) -> None:
    scope = BotCommandScopeDefault()

    try:
        for locale in SUPPORTED_LOCALES:
            lang_code = LOCALE_TO_TELEGRAM.get(locale, locale)
            localizer = Localizer(ctx.i18n.jinja_env, ctx.i18n.locales_data[locale])
            commands = await build_commands(localizer)

            if not commands:
                continue

            if lang_code == DEFAULT_LOCALE:
                await ctx.bot.set_my_commands(commands=commands, scope=scope)
            else:
                await ctx.bot.set_my_commands(
                    commands=commands,
                    scope=scope,
                    language_code=lang_code,
                )

        logger.info("Commands registered")

    except TelegramRetryAfter as e:
        logger.error(f"Failed to setup commands: \n{e.message}")


async def delete(ctx: Context) -> None:
    scope = BotCommandScopeDefault()

    try:
        for locale in SUPPORTED_LOCALES:
            lang_code = LOCALE_TO_TELEGRAM.get(locale, locale)

            if lang_code == DEFAULT_LOCALE:
                await ctx.bot.delete_my_commands(scope=scope)
            else:
                await ctx.bot.delete_my_commands(scope=scope, language_code=lang_code)

        logger.info("Commands deleted")

    except TelegramRetryAfter as e:
        logger.error(f"Failed to delete commands: \n{e.message}")
