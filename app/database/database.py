from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .models import BaseModel
from ..config import DB_URL

logger = logging.getLogger(__name__)


class Database:

    def __init__(self) -> None:
        self.engine: AsyncEngine = create_async_engine(
            url=DB_URL,
            connect_args={"timeout": 30},
            pool_pre_ping=True,
        )

        event.listen(self.engine.sync_engine, "connect", self._set_sqlite_pragmas)

        self.session_factory: async_sessionmaker = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    @staticmethod
    def _set_sqlite_pragmas(dbapi_connection: Any, _: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode = WAL;")
        cursor.execute("PRAGMA synchronous = NORMAL;")
        cursor.execute("PRAGMA cache_size = -20000;")  # ~20 MB
        cursor.execute("PRAGMA mmap_size = 268435456;")  # 256 MB
        cursor.execute("PRAGMA wal_autocheckpoint = 1000;")
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("PRAGMA temp_store = MEMORY;")
        cursor.close()

    async def start(self) -> None:
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(BaseModel.metadata.create_all)
            logger.info("Database schema initialized")
        except Exception:
            logger.error("Failed to initialize database")
            raise

    async def shutdown(self) -> None:
        try:
            await self.engine.dispose()
            logger.info("Database shutdown complete")
        except Exception:
            logger.error("Failed to shutdown database")
            raise
