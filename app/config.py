import typing as t
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

TONCENTER_API_KEY = ENV.str("TONCENTER_API_KEY")
MYTONPROVIDER_API_KEY = ENV.str("MYTONPROVIDER_API_KEY")
TELEMETRY_URL_SALT = "https://mytonprovider.org/api/v1/providers"
ADMIN_PASSWORD = ENV.str("ADMIN_PASSWORD")
