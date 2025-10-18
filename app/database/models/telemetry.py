from __future__ import annotations

import typing as t
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.schema import Index

from ._base import BaseModel
from ..helpers import now, now_rounded_min


class BaseTelemetryModel(BaseModel):
    __abstract__ = True

    provider_pubkey: Mapped[str] = mapped_column(
        ForeignKey("providers.pubkey"),
        primary_key=True,
        nullable=False,
    )

    bytes_recv: Mapped[t.Optional[int]] = mapped_column(BigInteger)
    bytes_sent: Mapped[t.Optional[int]] = mapped_column(BigInteger)
    cpu_info: Mapped[t.Optional[dict]] = mapped_column(JSON)
    disks_load: Mapped[t.Optional[dict[str, list[float]]]] = mapped_column(JSON)
    disks_load_percent: Mapped[t.Optional[dict[str, list[float]]]] = mapped_column(JSON)
    git_hashes: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    iops: Mapped[t.Optional[dict[str, list[float]]]] = mapped_column(JSON)
    net_load: Mapped[t.Optional[list[float]]] = mapped_column(JSON)
    net_recv: Mapped[t.Optional[list[float]]] = mapped_column(JSON)
    net_sent: Mapped[t.Optional[list[float]]] = mapped_column(JSON)
    pings: Mapped[t.Optional[dict[str, float]]] = mapped_column(JSON)
    pps: Mapped[t.Optional[list[float]]] = mapped_column(JSON)
    ram: Mapped[t.Optional[dict]] = mapped_column(JSON)
    storage: Mapped[dict] = mapped_column(JSON, nullable=False)
    swap: Mapped[t.Optional[dict]] = mapped_column(JSON)
    telemetry_pass: Mapped[t.Optional[str]] = mapped_column(String)
    timestamp: Mapped[t.Optional[int]] = mapped_column(Integer)
    uname: Mapped[t.Optional[dict]] = mapped_column(JSON)


class TelemetryModel(BaseTelemetryModel):
    __tablename__ = "telemetry"

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now,
        onupdate=now,
    )


class TelemetryHistoryModel(BaseTelemetryModel):
    __tablename__ = "telemetry_history"

    archived_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        nullable=False,
        default=now_rounded_min,
    )
    __table_args__ = (
        Index(
            "idx_telemetry_history_pubkey_archived",
            "provider_pubkey",
            "archived_at",
        ),
    )
