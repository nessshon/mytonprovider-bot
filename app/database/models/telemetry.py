from __future__ import annotations

import typing as t

from sqlalchemy import (
    String,
    ForeignKey,
    JSON,
    Integer,
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
    bytes_recv: Mapped[t.Optional[int]] = mapped_column(BigInteger)
    bytes_sent: Mapped[t.Optional[int]] = mapped_column(BigInteger)
    net_recv: Mapped[t.Optional[list[float]]] = mapped_column(JSON)
    net_sent: Mapped[t.Optional[list[float]]] = mapped_column(JSON)
    telemetry_pass: Mapped[t.Optional[str]] = mapped_column(String)
    timestamp: Mapped[t.Optional[int]] = mapped_column(Integer)

    raw: Mapped[t.Optional[dict]] = mapped_column(JSON)

    @property
    def raw_model(self) -> Telemetry:
        return Telemetry(**self.raw)
