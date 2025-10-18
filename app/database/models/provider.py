from __future__ import annotations

import typing as t
from datetime import datetime

from sqlalchemy import Boolean, BigInteger, DateTime, Float, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.schema import Index

from ._base import BaseModel
from ..helpers import now, now_rounded_min
from ...api.mytonprovider import TelemetryInfo
from ...bot.utils.ui import ProviderUI


class BaseProviderModel(BaseModel):
    __abstract__ = True

    pubkey: Mapped[str] = mapped_column(String(64), primary_key=True)

    location: Mapped[t.Optional[dict[str, str]]] = mapped_column(JSON)
    status: Mapped[t.Optional[int]] = mapped_column(Integer)
    address: Mapped[str] = mapped_column(String(64), nullable=False)
    uptime: Mapped[float] = mapped_column(Float, nullable=False)
    status_ratio: Mapped[t.Optional[float]] = mapped_column(Float)
    working_time: Mapped[int] = mapped_column(BigInteger, nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    max_span: Mapped[int] = mapped_column(BigInteger, nullable=False)
    price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    min_span: Mapped[int] = mapped_column(BigInteger, nullable=False)
    max_bag_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reg_time: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_send_telemetry: Mapped[bool] = mapped_column(Boolean, nullable=False)
    telemetry: Mapped[dict] = mapped_column(JSON)

    @property
    def telemetry_model(self) -> TelemetryInfo:
        return TelemetryInfo(**self.telemetry)

    @property
    def ui(self) -> ProviderUI:
        return ProviderUI(self)


class ProviderModel(BaseProviderModel):
    __tablename__ = "providers"

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now,
        onupdate=now,
    )


class ProviderHistoryModel(BaseProviderModel):
    __tablename__ = "providers_history"

    archived_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        nullable=False,
        default=now_rounded_min,
    )
    __table_args__ = (
        Index(
            "idx_providers_history_pubkey_archived",
            "pubkey",
            "archived_at",
        ),
    )
