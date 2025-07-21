import typing as t
from datetime import datetime
from typing import Any, Optional

from jinja2 import Environment
from sulguk import RenderResult

from ...config import TIMEZONE


class Localizer:

    def __init__(
        self,
        jinja_env: Environment,
        locale_data: t.Dict[str, t.Any],
    ) -> None:
        self.jinja_env = jinja_env
        self.locale_data = locale_data

        self.jinja_env.filters["datetimeformat"] = self._datetimeformat

    @staticmethod
    def _datetimeformat(ts: int, fmt="%Y-%m-%d %H:%M:%S") -> str:
        return datetime.fromtimestamp(ts, tz=TIMEZONE).strftime(fmt)

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

    def _get_locale(self, key: str, default: Optional[str] = None) -> Optional[str]:
        if key in self.locale_data:
            return self.locale_data[key]
        return self._get_nested(self.locale_data, key, default)

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
