import typing as t

from aiogram import BaseMiddleware
from aiogram.dispatcher.flags import get_flag
from aiogram.types import TelegramObject, User
from cachetools import TTLCache

THROTTLING_DEFAULT_KEY: str = "default"
THROTTLING_DEFAULT_TTL: float = 0.5


class ThrottlingMiddleware(BaseMiddleware):

    def __init__(
        self,
        *,
        default_key: t.Optional[str] = THROTTLING_DEFAULT_KEY,
        default_ttl: float = THROTTLING_DEFAULT_TTL,
        **ttl_map: float,
    ) -> None:
        if default_key:
            ttl_map[default_key] = default_ttl

        self.default_key = default_key
        self.caches: t.Dict[str, t.MutableMapping[int, None]] = {}

        for name, ttl in ttl_map.items():
            self.caches[name] = TTLCache(maxsize=10_000, ttl=ttl)

    async def __call__(
        self,
        handler: t.Callable[[TelegramObject, t.Dict[str, t.Any]], t.Awaitable[t.Any]],
        event: TelegramObject,
        data: t.Dict[str, t.Any],
    ) -> t.Optional[t.Any]:
        user: t.Optional[User] = data.get("event_from_user", None)

        if user is not None:
            throttling_key = get_flag(data, "throttling_key", default=self.default_key)
            if throttling_key and user.id in self.caches[throttling_key]:
                return None
            self.caches[throttling_key][user.id] = None

        return await handler(event, data)
