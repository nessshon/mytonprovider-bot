from __future__ import annotations

import logging
import typing as t
from pathlib import Path

import yaml
from jinja2 import Environment, StrictUndefined

from ....config import LOCALES_DIR, SUPPORTED_LOCALES

logger = logging.getLogger(__name__)


class I18N:

    def __init__(self) -> None:
        logger.info("Initializing i18n")
        self.jinja_env = Environment(
            autoescape=True,
            lstrip_blocks=True,
            trim_blocks=True,
            enable_async=True,
            undefined=StrictUndefined,
        )
        self.locales_data: t.Dict[str, t.Dict[str, t.Any]] = self._load_all_locales()

    def _load_all_locales(self) -> t.Dict[str, t.Dict[str, t.Any]]:
        if not LOCALES_DIR.is_dir():
            logger.error(f"Locales directory is missing: {str(LOCALES_DIR)}")
            raise FileNotFoundError(
                f"Locales directory '{LOCALES_DIR}' does not exist or is not a directory."
            )

        locales_data: t.Dict[str, t.Dict[str, t.Any]] = {}
        for locale in SUPPORTED_LOCALES:
            try:
                file_path = self._resolve_locale_file(locale)
                raw_data = self._load_yaml_file(file_path)
                expanded = self._expand_dotted_keys(raw_data)
                locales_data[locale] = expanded
                logger.info(f"Locale loaded: '{locale}'")
            except Exception:
                logger.error(f"Failed to load locale: '{locale}'")
                raise

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
    def _load_yaml_file(file_path: Path) -> t.Dict[str, t.Any]:
        try:
            with file_path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            logger.error(f"YAML parse error: 'file={str(file_path)}'")
            raise ValueError(f"Failed to parse YAML file '{file_path}': {e}") from e
        if not isinstance(data, dict):
            logger.error(
                "Invalid locale structure: "
                f"'file={str(file_path)}, type={type(data).__name__}'",
            )
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
