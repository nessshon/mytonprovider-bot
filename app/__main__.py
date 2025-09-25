import logging
from contextlib import suppress

from aiogram import Dispatcher, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramRetryAfter
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage
from aiogram_dialog import setup_dialogs
from redis.asyncio import Redis
from sulguk import SULGUK_PARSE_MODE

from .api.mytonprovider import MytonproviderClient
from .api.toncenter import ToncenterClient
from .bot import commands, middlewares, handlers, dialogs
from .bot.broadcaster import Broadcaster
from .bot.utils.i18n import I18N
from .config import BOT_TOKEN, REDIS_URL
from .context import Context, set_context
from .database.database import Database
from .logging import setup_logging
from .scheduler.scheduler import Scheduler

setup_logging()
logger = logging.getLogger("app.main")


async def on_startup(ctx: Context) -> None:
    logger.info("App startup initiated...")

    await ctx.db.start()
    await ctx.scheduler.start()

    middlewares.register(ctx.dp, ctx.bot)
    handlers.register(ctx.dp)
    dialogs.register(ctx.dp)
    setup_dialogs(ctx.dp)

    with suppress(TelegramRetryAfter):
        await commands.setup(ctx)
    logger.info("App startup complete")


async def on_shutdown(ctx: Context) -> None:
    logger.info("App shutdown initiated...")

    with suppress(TelegramRetryAfter):
        await commands.delete(ctx)
    await ctx.bot.session.close()

    await ctx.scheduler.shutdown()
    await ctx.db.shutdown()
    logger.info("App shutdown complete")


async def main() -> None:
    logger.info("Preparing app...")

    ctx = Context()
    ctx.db = Database()
    ctx.scheduler = Scheduler()
    ctx.redis = Redis.from_url(url=REDIS_URL)

    properties = DefaultBotProperties(
        parse_mode=SULGUK_PARSE_MODE,
        link_preview_is_disabled=True,
    )
    storage = RedisStorage(
        redis=ctx.redis,
        key_builder=DefaultKeyBuilder(with_destiny=True),
    )
    ctx.bot = Bot(BOT_TOKEN, default=properties)
    ctx.dp = Dispatcher(storage=storage, ctx=ctx)

    ctx.broadcaster = Broadcaster(ctx.bot)
    ctx.toncenter = ToncenterClient()
    ctx.mytonprovider = MytonproviderClient()
    ctx.i18n = I18N()

    ctx.dp.startup.register(on_startup)
    ctx.dp.shutdown.register(on_shutdown)
    set_context(ctx)

    allowed_updates = ctx.dp.resolve_used_update_types()
    await ctx.dp.start_polling(ctx.bot, allowed_updates=allowed_updates)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
