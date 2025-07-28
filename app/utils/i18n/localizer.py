from __future__ import annotations

import typing as t
from datetime import datetime, timedelta
from typing import Any, Optional

from jinja2 import Environment
from sulguk import RenderResult


class Localizer:

    def __init__(
        self,
        jinja_env: Environment,
        locale_data: t.Dict[str, t.Any],
    ) -> None:
        self.jinja_env = jinja_env
        self.locale_data = locale_data

        self.jinja_env.filters["toamount"] = self._toamount_filter
        self.jinja_env.filters["datetimeformat"] = self._datetimeformat_filter
        self.jinja_env.filters["durationformat"] = self._durationformat_filter

    @staticmethod
    async def _toamount_filter(value: t.Optional[int]) -> str:
        if value is None:
            return "0"
        return f"{value / 1e9:.4f}".rstrip("0").rstrip(".")

    @staticmethod
    async def _datetimeformat_filter(
        ts: t.Optional[t.Union[int, datetime]],
        fmt: str = "%Y-%m-%d %H:%M",
    ) -> str:
        if ts is None:
            return "N/A"
        if isinstance(ts, int):
            ts = datetime.fromtimestamp(ts)
        return ts.strftime(fmt)

    async def _durationformat_filter(self, seconds: t.Optional[int]) -> str:
        if seconds is None:
            return "N/A"
        delta = timedelta(seconds=seconds)
        days = delta.days
        hours = delta.seconds // 3600

        async def l(key: str) -> str:
            return await self(f"duration_short.{key}")

        if days > 365:
            years = days // 365
            rem_days = days % 365
            return f"{years}{await l('year')} {rem_days}{await l('day')}"
        elif days > 0:
            return f"{days}{await l('day')} {hours}{await l('hour')}"
        return f"{hours}{await l('hour')}"

    @classmethod
    def _get_nested(
        cls, data: t.Dict[str, t.Any], dotted_key: str, default: Optional[Any] = None
    ) -> Any:
        keys = dotted_key.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def _get_locale(self, key: str, default: Optional[str] = None) -> Optional[str]:
        if key in self.locale_data:
            return self.locale_data[key]
        return self._get_nested(self.locale_data, key, default)

    def render_sync(self, key: str, **kwargs) -> str:
        template_str = self._get_locale(key)
        if template_str is None:
            return key
        template = self.jinja_env.from_string(template_str)
        return template.render(**kwargs)

    async def __call__(
        self,
        key: Optional[str] = None,
        *,
        default: Optional[str] = None,
        **kwargs: t.Any,
    ) -> t.Union[str, RenderResult]:
        if key is not None:
            template_str = self._get_locale(key)
            if template_str is None:
                raise KeyError(f"Localization key '{key}' not found in locale data.")
        elif default is not None:
            template_str = default
        else:
            raise ValueError("Either 'key' or 'default' must be provided to Localizer.")

        try:
            template = self.jinja_env.from_string(template_str)
            text = await template.render_async(**kwargs)
        except (Exception,):
            return template_str
        return text
