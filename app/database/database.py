from __future__ import annotations

import logging

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
        self.session_factory: async_sessionmaker = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

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
