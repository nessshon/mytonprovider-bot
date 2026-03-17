import typing as t
from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from ._base import BaseModel
from ..helpers import now


class BagModel(BaseModel):
    __tablename__ = "bags"

    provider_pubkey: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        nullable=False,
    )
    bags: Mapped[t.List[str]] = mapped_column(JSON, default=list)
    bags_count: Mapped[int] = mapped_column(Integer, default=0)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now,
        onupdate=now,
        nullable=True,
    )
