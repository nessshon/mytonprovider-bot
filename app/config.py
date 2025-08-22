from __future__ import annotations

import logging
import sys
import typing as t
from logging.handlers import TimedRotatingFileHandler
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


def setup_logging(
    log_file_name: str = "app.log",
    keep_days: int = 7,
    use_utc: bool = False,
) -> None:
    level = logging.INFO
    logs_dir = BASE_DIR.parent / ".logs"
    logs_dir.mkdir(exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-10s | %(name)-50s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = TimedRotatingFileHandler(
        filename=logs_dir / log_file_name,
        when="midnight",
        interval=1,
        backupCount=keep_days,
        encoding="utf-8",
        utc=use_utc,
    )
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    logging.getLogger("aiogram").setLevel(logging.WARNING)
