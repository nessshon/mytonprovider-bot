from __future__ import annotations

import asyncio
import typing as t

_CTX: t.Optional[Context] = None
_STORAGE_KEY: str = "__context_storage__"


class Context:

    @classmethod
    def _storage(cls) -> dict[str, t.Any]:
        loop = asyncio.get_running_loop()
        if not hasattr(loop, _STORAGE_KEY):
            setattr(loop, _STORAGE_KEY, {})
        return getattr(loop, _STORAGE_KEY)

    def __getattr__(self, name: str) -> t.Any:
        try:
            return self._storage()[name]
        except KeyError:
            raise AttributeError(f"Context has no attribute '{name}'")

    def __setattr__(self, name: str, value: t.Any) -> None:
        self._storage()[name] = value

    def __delattr__(self, name: str) -> None:
        try:
            del self._storage()[name]
        except KeyError:
            raise AttributeError(f"Context has no attribute '{name}'")

    def __contains__(self, name: str) -> bool:
        return name in self._storage()


def set_context(ctx: Context) -> None:
    global _CTX
    _CTX = ctx


def get_context() -> Context:
    if _CTX is None:
        raise RuntimeError("Context has not been set")
    return _CTX
