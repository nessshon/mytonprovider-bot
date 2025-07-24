from __future__ import annotations

import typing as t
from typing import TypeVar

from sqlalchemy import (
    delete,
    exists,
    func,
    select,
    update,
    Delete,
    Select,
    Update,
)
from sqlalchemy.ext.asyncio import AsyncSession

from .models import BaseModel

_TModel = TypeVar("_TModel", bound=BaseModel)
_TStmt = t.TypeVar("_TStmt", bound=t.Union[Select, Update, Delete])


class BaseRepository(t.Generic[_TModel]):

    def __init__(self, model: t.Type[_TModel], session: AsyncSession) -> None:
        self.model: t.Type[_TModel] = model
        self.session: AsyncSession = session

    def _build_filters(
            self,
            stmt: _TStmt,
            filters: t.Dict[str, t.Any],
    ) -> _TStmt:
        for field, value in filters.items():
            column = getattr(self.model, field)
            cond = column.in_(value) if isinstance(value, list) else column == value
            stmt = stmt.where(cond)
        return stmt

    async def upsert(self, model: _TModel) -> _TModel:
        pk_columns = self.model.__mapper__.primary_key
        pk_filter = {col.key: getattr(model, col.key) for col in pk_columns}

        existing = await self.get(**pk_filter)
        if existing:
            for field in model.__table__.columns.keys():
                if field not in pk_filter:
                    setattr(existing, field, getattr(model, field))
            await self.session.flush()
            return existing

        return await self.create(model)

    async def create(self, model: _TModel) -> _TModel:
        self.session.add(model)
        await self.session.flush()
        return model

    async def get(self, **filters: t.Any) -> t.Optional[_TModel]:
        stmt: Select = select(self.model)
        stmt = self._build_filters(stmt, filters).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
            self,
            *,
            offset: int = 0,
            limit: int = 20,
            order_by: t.Optional[t.Any] = None,
            **filters: t.Any,
    ) -> t.List[_TModel]:
        stmt: Select = select(self.model)
        stmt = self._build_filters(stmt, filters)

        if order_by is not None:
            order_by_list = order_by if isinstance(order_by, list) else [order_by]
            stmt = stmt.order_by(*order_by_list)

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def all(self) -> t.List[_TModel]:
        stmt: Select = select(self.model)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(
            self,
            filters: t.Dict[str, t.Any],
            values: t.Dict[str, t.Any],
    ) -> t.Optional[_TModel]:
        stmt: Update = update(self.model).values(**values).returning(self.model)
        stmt = self._build_filters(stmt, filters)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, **filters: t.Any) -> None:
        stmt: Delete = delete(self.model)
        stmt = self._build_filters(stmt, filters)
        await self.session.execute(stmt)

    async def count(self, **filters: t.Any) -> int:
        stmt: Select = select(func.count()).select_from(self.model)
        stmt = self._build_filters(stmt, filters)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def exists(self, **filters: t.Any) -> bool:
        filtered = self._build_filters(select(self.model), filters)
        stmt: Select = select(exists(filtered.subquery()))
        result = await self.session.execute(stmt)
        return result.scalar()
