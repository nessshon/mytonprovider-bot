from __future__ import annotations

import typing as t
from pathlib import Path

import yaml
from jinja2 import Environment

from ...config import LOCALES_DIR, SUPPORTED_LOCALES


class I18N:

    def __init__(self) -> None:
        self.jinja_env = Environment(
            autoescape=True,
            lstrip_blocks=True,
            trim_blocks=True,
            enable_async=True,
        )
        self.locales_data: t.Dict[str, t.Dict[str, t.Any]] = self._load_all_locales()

    def _load_all_locales(self) -> t.Dict[str, t.Dict[str, t.Any]]:
        if not LOCALES_DIR.is_dir():
            raise FileNotFoundError(
                f"Locales directory '{LOCALES_DIR}' does not exist or is not a directory."
            )

        locales_data: t.Dict[str, t.Dict[str, t.Any]] = {}
        for locale in SUPPORTED_LOCALES:
            file_path = self._resolve_locale_file(locale)
            raw_data = self._load_yaml_file(file_path)
            locales_data[locale] = self._expand_dotted_keys(raw_data)

        return locales_data

    @staticmethod
    def _resolve_locale_file(locale: str) -> Path:
        for ext in ("yaml", "yml"):
            candidate = LOCALES_DIR / f"{locale}.{ext}"
            if candidate.exists():
                return candidate
        raise FileNotFoundError(
            f"Locale file for '{locale}' not found (.yaml or .yml) in '{LOCALES_DIR}'"
        )

    @staticmethod
    def _load_yaml_file(file_path: Path) -> LocaleData:
        try:
            with file_path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML file '{file_path}': {e}") from e
        if not isinstance(data, dict):
            raise TypeError(
                f"Locale file '{file_path}' must contain a top-level dictionary"
            )
        return data

    @staticmethod
    def _expand_dotted_keys(flat: dict[str, t.Any]) -> dict[str, t.Any]:
        result: dict[str, t.Any] = {}

        for key, value in flat.items():
            if "." not in key:
                result[key] = value
                continue

            parts = key.split(".")
            current = result
            for part in parts[:-1]:
                current = current.setdefault(part, {})
            current[parts[-1]] = value

        return result
