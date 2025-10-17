from __future__ import annotations

import json
import typing as t

from sqlalchemy.orm import DeclarativeBase, InstrumentedAttribute

_T = t.TypeVar("_T", bound="BaseModel")


class BaseModel(DeclarativeBase):
    __repr_cols__: tuple[str, ...] = ()
    __repr_cols_num__: int = 10

    def __repr__(self) -> str:
        cols = ", ".join(
            f"{col}={getattr(self, col)!r}"
            for idx, col in enumerate(self.__table__.columns.keys())
            if col in self.__repr_cols__ or idx < self.__repr_cols_num__
        )
        return f"<{self.__class__.__name__} {cols}>"

    @property
    def pk(self) -> int:
        return getattr(self, self.get_pk_column().key)

    def get_pk(self):
        return getattr(self, self.get_pk_column().name)

    @classmethod
    def get_pk_column(cls) -> InstrumentedAttribute:  # noqa
        pk_cols = cls.__mapper__.primary_key
        if len(pk_cols) != 1:
            raise ValueError(f"{cls.__name__} has composite or missing PK")
        return getattr(cls, pk_cols[0].key)

    def get_col(self, name: str) -> t.Any:
        try:
            return getattr(self, name)
        except AttributeError as e:
            raise ValueError(f"Model {self.__name__} has no column '{name}'") from e

    def model_dump(
        self,
        *,
        exclude_none: bool = True,
        exclude: t.Optional[t.Iterable[t.Union[str, InstrumentedAttribute]]] = None,
    ) -> dict[str, t.Any]:
        exclude_set = {
            item.key if isinstance(item, InstrumentedAttribute) else str(item)
            for item in exclude or ()
        }

        result = {
            col: getattr(self, col)
            for col in self.__table__.columns.keys()
            if col not in exclude_set
        }

        if exclude_none:
            result = {k: v for k, v in result.items() if v is not None}

        return result

    def model_dump_json(self) -> str:
        return json.dumps(self.model_dump(), default=str)

    @classmethod
    def from_json(cls: t.Type[_T], json_str: str) -> _T:
        data = json.loads(json_str)
        return cls(**data)
