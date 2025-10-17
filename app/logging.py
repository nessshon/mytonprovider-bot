import logging
import sys
from logging.handlers import TimedRotatingFileHandler

from .config import BASE_DIR


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
