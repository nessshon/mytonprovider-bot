from datetime import datetime

from ..config import TIMEZONE


def now() -> datetime:
    return datetime.now(TIMEZONE)


def round_to_minute(dt: datetime) -> datetime:
    return dt.replace(second=0, microsecond=0)


def round_to_hour(dt: datetime) -> datetime:
    return dt.replace(minute=0, second=0, microsecond=0)


def now_rounded_min() -> datetime:
    return round_to_minute(now())


def now_rounded_hour() -> datetime:
    return round_to_hour(now())
