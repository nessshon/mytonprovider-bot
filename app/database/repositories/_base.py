from __future__ import annotations

import abc
import typing as t
from typing import TypeVar

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import BaseModel

_TBaseModel = TypeVar("_TBaseModel", bound=BaseModel)


class AbstractRepository(abc.ABC, t.Generic[_TBaseModel]):

    @abc.abstractmethod
    async def create(self, **kwargs: t.Any) -> _TBaseModel: ...

    @abc.abstractmethod
    async def get(self, **filters: t.Any) -> t.Optional[_TBaseModel]: ...

    @abc.abstractmethod
    async def list(
        self,
        order_by: t.Optional[t.Any] = None,
        **filters: t.Any,
    ) -> t.List[_TBaseModel]: ...

    @abc.abstractmethod
    async def update(
        self,
        filters: dict[str, t.Any],
        values: dict[str, t.Any],
    ) -> t.Optional[_TBaseModel]: ...

    @abc.abstractmethod
    async def delete(self, **filters: t.Any) -> None: ...


class BaseRepository(AbstractRepository[_TBaseModel]):
    model: t.Type[_TBaseModel]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _apply_filters(
        stmt,
        model: _TBaseModel,
        filters: dict[str, t.Any],
    ):
        for field, value in filters.items():
            column = getattr(model, field)
            if isinstance(value, list):
                stmt = stmt.where(column.in_(value))
            else:
                stmt = stmt.where(column == value)
        return stmt

    async def upsert(self, model: _TBaseModel) -> _TBaseModel:
        existing = await self.get(**{self.model.get_pk_column().name: model.get_pk()})
        if existing:
            for field in model.__table__.columns.keys():
                setattr(existing, field, getattr(model, field))
            await self.session.flush()
            return existing
        else:
            return await self.create(model)

    async def create(self, model: _TBaseModel) -> _TBaseModel:
        self.session.add(model)
        await self.session.flush()
        return model

    async def get(self, **filters: t.Any) -> t.Optional[_TBaseModel]:
        stmt = select(self.model)
        stmt = self._apply_filters(stmt, self.model, filters).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        order_by: t.Optional[t.Any] = None,
        **filters: t.Any,
    ) -> list[_TBaseModel]:
        stmt = select(self.model)
        stmt = self._apply_filters(stmt, self.model, filters)

        if order_by is not None:
            if isinstance(order_by, list):
                stmt = stmt.order_by(*order_by)
            else:
                stmt = stmt.order_by(order_by)

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self,
        filters: dict[str, t.Any],
        values: dict[str, t.Any],
    ) -> t.Optional[_TBaseModel]:
        stmt = update(self.model).values(**values).returning(self.model)
        stmt = self._apply_filters(stmt, self.model, filters)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, **filters: t.Any) -> None:
        stmt = delete(self.model)
        stmt = self._apply_filters(stmt, self.model, filters)
        await self.session.execute(stmt)

    async def count(self, **filters: t.Any) -> int:
        stmt = select(func.count()).select_from(self.model)
        stmt = self._apply_filters(stmt, self.model, filters)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def exists(self, **filters: t.Any) -> bool:
        stmt = select(self.model)
        stmt = self._apply_filters(stmt, self.model, filters).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
