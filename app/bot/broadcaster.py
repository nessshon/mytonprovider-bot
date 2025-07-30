import asyncio
import typing as t

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import InlineKeyboardMarkup, BufferedInputFile


class Broadcaster:

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._lock = asyncio.Lock()

    async def _retry(
        self,
        func: t.Callable[..., t.Awaitable],
        *args,
        max_retries: int = 10,
        **kwargs,
    ) -> bool:
        for _ in range(max_retries):
            async with self._lock:
                try:
                    await func(*args, **kwargs)
                    return True
                except TelegramRetryAfter as e:
                    await asyncio.sleep(e.retry_after)
                except (Exception,):
                    return False
        return False

    async def send_message(
        self,
        user_id: int,
        text: str,
        reply_markup: t.Optional[InlineKeyboardMarkup] = None,
        max_retries: int = 10,
    ) -> bool:
        return await self._retry(
            self.bot.send_message,
            chat_id=user_id,
            text=text,
            reply_markup=reply_markup,
            max_retries=max_retries,
        )

    async def send_document(
        self,
        user_id: int,
        document: BufferedInputFile,
        caption: t.Optional[str] = None,
        max_retries: int = 10,
    ) -> bool:
        return await self._retry(
            self.bot.send_document,
            chat_id=user_id,
            document=document,
            caption=caption,
            max_retries=max_retries,
        )
