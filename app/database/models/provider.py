from __future__ import annotations

from datetime import date, timedelta

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
    def short_pubkey(self) -> str:
        return f"{self.pubkey[:8]}...{self.pubkey[-8:]}"

    @property
    def price_display(self) -> str:
        return f"{self.price / 1e9:.2f}"

    @property
    def min_span_display(self) -> str:
        return self._format_duration_display(self.min_span)

    @property
    def max_span_display(self) -> str:
        return self._format_duration_display(self.max_span)

    @property
    def working_time_display(self) -> str:
        return self._format_duration_display(self.working_time)

    @staticmethod
    def _format_duration_display(seconds: int) -> str:
        delta = timedelta(seconds=seconds)
        days = delta.days
        hours = delta.seconds // 3600
        if days > 365:
            years = days // 365
            rem_days = days % 365
            return f"{years} year{'s' if years > 1 else ''} {rem_days} days"
        if days > 0:
            return f"{days} days {hours} hr"
        return f"{hours} hr"

    @property
    def status_emoji_display(self) -> str:
        ratio = self.uptime / 100 if self.uptime else 0
        if self.status is None:
            return "⚪️"
        if self.status == 0:
            if ratio < 0.8:
                return "🔴"
            elif ratio < 0.99:
                return "🟡"
            else:
                return "🟢"
        if self.status == 2:
            return "🟠"
        if self.status == 3:
            return "🚫"
        if self.status == 500:
            return "⚫️"
        return "⚪️"

    @property
    def status_text_display(self) -> str:
        ratio = self.uptime / 100 if self.uptime else 0
        if self.status is None:
            return "No Data"
        if self.status == 0:
            if ratio < 0.8:
                return "Unstable"
            elif ratio < 0.99:
                return "Partial"
            else:
                return "Stable"
        if self.status == 2:
            return "Invalid"
        if self.status == 3:
            return "Not Store"
        if self.status == 500:
            return "Not Accessible"
        return "Unknown"


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
