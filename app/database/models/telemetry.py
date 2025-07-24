from __future__ import annotations

import typing as t
from datetime import date

from sqlalchemy import (
    String,
    ForeignKey,
    JSON,
    Integer,
    Float,
    Date,
    BigInteger,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from ._base import BaseModel
from ...utils.mtpapi.models import Telemetry


class TelemetryModel(BaseModel):
    __tablename__ = "telemetry"

    provider_pubkey: Mapped[str] = mapped_column(
        ForeignKey("providers.pubkey"),
        primary_key=True,
        nullable=False,
    )

    storage: Mapped[dict] = mapped_column(JSON, nullable=False)
    git_hashes: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)

    net_load: Mapped[t.Optional[list[float]]] = mapped_column(JSON)
    disks_load: Mapped[t.Optional[dict[str, list[float]]]] = mapped_column(JSON)
    disks_load_percent: Mapped[t.Optional[dict[str, list[float]]]] = mapped_column(JSON)
    iops: Mapped[t.Optional[dict[str, list[float]]]] = mapped_column(JSON)
    pps: Mapped[t.Optional[list[float]]] = mapped_column(JSON)

    ram: Mapped[t.Optional[dict]] = mapped_column(JSON)
    swap: Mapped[t.Optional[dict]] = mapped_column(JSON)
    uname: Mapped[t.Optional[dict]] = mapped_column(JSON)
    cpu_info: Mapped[t.Optional[dict]] = mapped_column(JSON)
    pings: Mapped[t.Optional[dict[str, float]]] = mapped_column(JSON)
    benchmark: Mapped[t.Optional[dict]] = mapped_column(JSON)

    x_real_ip: Mapped[str] = mapped_column(String, nullable=False)

    raw: Mapped[t.Optional[dict]] = mapped_column(JSON)

    @property
    def raw_model(self) -> Telemetry:
        return Telemetry(**self.raw)


class TelemetryHistoryModel(BaseModel):
    __tablename__ = "telemetry.history"

    provider_pubkey: Mapped[str] = mapped_column(String(64), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)

    wallet_address: Mapped[str] = mapped_column(String(64))

    total_provider_space: Mapped[float] = mapped_column(Float)
    used_provider_space: Mapped[float] = mapped_column(Float)
    bags_count: Mapped[int] = mapped_column(Integer)
    traffic_in: Mapped[float] = mapped_column(Float)
    traffic_out: Mapped[float] = mapped_column(Float)

    ton_balance: Mapped[int] = mapped_column(BigInteger)
    ton_earned: Mapped[int] = mapped_column(BigInteger)
