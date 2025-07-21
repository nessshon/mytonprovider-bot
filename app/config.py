from __future__ import annotations

import typing as t
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from environs import Env

ENV = Env()
ENV.read_env()

BASE_DIR = Path(__file__).resolve().parent
TIMEZONE = ZoneInfo(ENV.str("TIMEZONE", "UTC"))

LOCALES_DIR: Path = BASE_DIR.parent / "locales"
DEFAULT_LOCALE: str = ENV.str("DEFAULT_LOCALE", "en")
SUPPORTED_LOCALES: t.List[str] = ENV.list("SUPPORTED_LOCALES", default=[DEFAULT_LOCALE])

DEV_ID: int = ENV.int("DEV_ID")
ADMIN_IDS: list = ENV.list("ADMIN_IDS", subcast=int, default=[])

DB_URL = ENV.str("DB_URL")
REDIS_URL = ENV.str("REDIS_URL")
SCHEDULER_URL = ENV.str("SCHEDULER_URL")

BOT_TOKEN: str = ENV.str("BOT_TOKEN")


@dataclass(frozen=True)
class ExternalLinks:
    WEBSITE: str = "https://mytonprovider.org/"
    CHAT: str = "https://t.me/mytonprovider_chat"
    BECOME_PROVIDER: str = (
        "https://github.com/igroman787/mytonprovider/blob/master/README.md"
    )
