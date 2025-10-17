from __future__ import annotations

import logging
import typing as t
from datetime import datetime, timedelta

from jinja2 import Environment
from sulguk import RenderResult

logger = logging.getLogger(__name__)


class Localizer:

    def __init__(
        self,
        jinja_env: Environment,
        locale_data: t.Dict[str, t.Any],
    ) -> None:
        self.jinja_env = jinja_env
        self.locale_data = locale_data

        self.jinja_env.filters["toamount"] = self._toamount_filter
        self.jinja_env.filters["sizeformat"] = self._sizeformat_filter
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

    @staticmethod
    async def _sizeformat_filter(value: t.Optional[t.Union[int, float]]) -> str:
        if value is None:
            return "0MB"

        try:
            b = float(value)
        except (Exception,):
            return "0MB"

        sign = "-" if b < 0 else ""
        b = abs(b)

        units = [
            ("MB", 1e6),
            ("GB", 1e9),
            ("TB", 1e12),
            ("PB", 1e15),
            ("EB", 1e18),
            ("ZB", 1e21),
            ("YB", 1e24),
        ]

        for name, factor in reversed(units):
            if b >= factor:
                num = b / factor
                break
        else:
            name, factor = units[0]
            num = b / factor

        s = f"{num:.2f}".rstrip("0").rstrip(".")
        return f"{sign}{s}{name}"

    @classmethod
    def _get_nested(
        cls,
        data: t.Dict[str, t.Any],
        dotted_key: str,
        default: t.Optional[t.Any] = None,
    ) -> t.Any:
        keys = dotted_key.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def _get_locale(self, key: str, default: t.Optional[str] = None) -> t.Optional[str]:
        if key in self.locale_data:
            return self.locale_data[key]

        result = self._get_nested(self.locale_data, key, default)
        if result is default:
            logger.info(f"Localization key not found: 'key={key}'")

        return result

    def render_sync(self, key: str, **kwargs) -> str:
        template_str = self._get_locale(key)
        if template_str is None:
            return key
        template = self.jinja_env.from_string(template_str)
        return template.render(**kwargs)

    async def __call__(
        self,
        key: t.Optional[str] = None,
        *,
        default: t.Optional[str] = None,
        **kwargs: t.Any,
    ) -> t.Union[str, RenderResult]:
        if key is not None:
            template_str = self._get_locale(key)
            if template_str is None:
                logger.warning(f"Missing localization key: 'key={key}'")
                raise KeyError(f"Localization key '{key}' not found in locale data.")
        elif default is not None:
            template_str = default
        else:
            raise ValueError("Either 'key' or 'default' must be provided to Localizer.")

        try:
            template = self.jinja_env.from_string(template_str)
            text = await template.render_async(**kwargs)
        except (Exception,):
            logger.warning(f"Template rendering failed: 'key={key}'")
            return template_str

        return text
