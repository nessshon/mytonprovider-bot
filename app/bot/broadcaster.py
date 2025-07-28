import asyncio
import typing as t

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import InlineKeyboardMarkup


class Broadcaster:

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._lock = asyncio.Lock()

    async def send_message(
        self,
        user_id: int,
        text: str,
        reply_markup: t.Optional[InlineKeyboardMarkup] = None,
        max_retries: int = 10,
    ) -> bool:
        for _ in range(max_retries):
            async with self._lock:
                try:
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=text,
                        reply_markup=reply_markup,
                    )
                    return True
                except TelegramRetryAfter as e:
                    await asyncio.sleep(e.retry_after)
                except (Exception,):
                    return False
        return False
