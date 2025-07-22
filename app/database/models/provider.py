from __future__ import annotations

from datetime import date

from sqlalchemy import (
    BigInteger,
    String,
    JSON,
    Float,
    Integer,
    Boolean,
    ForeignKey,
    Date,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from ._base import BaseModel
from .display import ProviderDisplay
from ...utils.mtpapi.models import Telemetry


class ProviderModel(BaseModel):
    __tablename__ = "providers"

    pubkey: Mapped[str] = mapped_column(String(64), primary_key=True)
    address: Mapped[str] = mapped_column(String(64), nullable=False)

    uptime: Mapped[float] = mapped_column(Float, nullable=False)
    working_time: Mapped[int] = mapped_column(Integer, nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    max_span: Mapped[int] = mapped_column(Integer, nullable=False)
    min_span: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    max_bag_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reg_time: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[int] = mapped_column(Integer, nullable=False)
    is_send_telemetry: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Simple telemetry raw API response
    telemetry_raw: Mapped[dict] = mapped_column(JSON, default=dict)

    telemetry: Mapped[TelemetryModel] = relationship(
        back_populates="provider",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="joined",
    )

    @property
    def simple_telemetry(self) -> Telemetry:
        return Telemetry(**self.telemetry_raw)

    @property
    def display(self) -> ProviderDisplay:
        return ProviderDisplay(self)


class TelemetryModel(BaseModel):
    __tablename__ = "provider_telemetry"

    provider_pubkey: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("providers.pubkey", ondelete="CASCADE"),
        primary_key=True,
    )
    storage_pubkey: Mapped[str] = mapped_column(String(64))
    storage_disk_name: Mapped[str] = mapped_column(String(64))

    # Storage volumes (in GiB)
    storage_used_disk_space: Mapped[float] = mapped_column(Float)
    storage_total_disk_space: Mapped[float] = mapped_column(Float)
    provider_used_provider_space: Mapped[float] = mapped_column(Float)
    provider_total_provider_space: Mapped[float] = mapped_column(Float)

    # RAM
    ram_total: Mapped[float] = mapped_column(Float)
    ram_usage: Mapped[float] = mapped_column(Float)
    ram_usage_percent: Mapped[float] = mapped_column(Float)

    # CPU
    cpu_count: Mapped[int] = mapped_column(Integer)
    cpu_name: Mapped[str] = mapped_column(String)
    cpu_is_virtual: Mapped[bool] = mapped_column(Boolean)
    cpu_load: Mapped[list[float]] = mapped_column(JSON, default=list)

    # Network
    net_load: Mapped[list[float]] = mapped_column(JSON, default=list)
    net_pps: Mapped[list[float]] = mapped_column(JSON, default=list)
    net_pings: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    net_x_real_ip: Mapped[str] = mapped_column(String(64))

    # Disks
    disk_iops: Mapped[dict[str, list]] = mapped_column(JSON, default=dict)
    disk_load_percent: Mapped[dict[str, list]] = mapped_column(JSON, default=dict)

    # System info
    system_sysname: Mapped[str] = mapped_column(String)
    system_release: Mapped[str] = mapped_column(String)
    system_version: Mapped[str] = mapped_column(String)
    system_machine: Mapped[str] = mapped_column(String)

    # Full raw API response
    raw: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    provider: Mapped[ProviderModel] = relationship(
        back_populates="telemetry",
        uselist=False,
    )


class TelemetryHistoryModel(BaseModel):
    __tablename__ = "telemetry_history"

    provider_pubkey: Mapped[str] = mapped_column(String(64), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)

    # Storage / Disk usage
    used_provider_space: Mapped[float] = mapped_column(Float)
    total_provider_space: Mapped[float] = mapped_column(Float)
    used_disk_space: Mapped[float] = mapped_column(Float)
    total_disk_space: Mapped[float] = mapped_column(Float)

    # Bags (future, from mytonprovider.org)
    bags_count: Mapped[int] = mapped_column(Integer)

    # Traffic (future)
    traffic_in: Mapped[float] = mapped_column(Float)
    traffic_out: Mapped[float] = mapped_column(Float)

    # Earnings (future, from blockchain)
    ton_balance: Mapped[float] = mapped_column(Float)
    ton_earned: Mapped[float] = mapped_column(Float)
