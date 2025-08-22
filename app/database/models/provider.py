from __future__ import annotations

import typing as t
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    String,
    Float,
    Integer,
    Boolean,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.sql.sqltypes import DateTime

from ._base import BaseModel
from ...utils.mtpapi.models import Provider, Telemetry


class ProviderTelemetryModel(BaseModel):
    __tablename__ = "providers.telemetry"

    provider_pubkey: Mapped[str] = mapped_column(
        ForeignKey("providers.pubkey"),
        primary_key=True,
        nullable=False,
    )

    storage_git_hash: Mapped[t.Optional[str]] = mapped_column(String)
    provider_git_hash: Mapped[t.Optional[str]] = mapped_column(String)
    qd64_disk_read_speed: Mapped[t.Optional[str]] = mapped_column(String)
    qd64_disk_write_speed: Mapped[t.Optional[str]] = mapped_column(String)
    country: Mapped[t.Optional[str]] = mapped_column(String)
    isp: Mapped[t.Optional[str]] = mapped_column(String)
    cpu_name: Mapped[t.Optional[str]] = mapped_column(String)
    updated_at: Mapped[t.Optional[int]] = mapped_column(BigInteger)

    total_provider_space: Mapped[t.Optional[float]] = mapped_column(Float)
    used_provider_space: Mapped[t.Optional[float]] = mapped_column(Float)
    total_ram: Mapped[t.Optional[float]] = mapped_column(Float)
    usage_ram: Mapped[t.Optional[float]] = mapped_column(Float)
    ram_usage_percent: Mapped[t.Optional[float]] = mapped_column(Float)
    speedtest_download: Mapped[t.Optional[int]] = mapped_column(Float)
    speedtest_upload: Mapped[t.Optional[int]] = mapped_column(Float)
    speedtest_ping: Mapped[t.Optional[float]] = mapped_column(Float)
    cpu_number: Mapped[t.Optional[int]] = mapped_column(Integer)
    cpu_is_virtual: Mapped[t.Optional[bool]] = mapped_column(Boolean)

    raw: Mapped[t.Optional[dict]] = mapped_column(JSON)

    provider: Mapped[ProviderModel] = relationship(
        back_populates="telemetry",
        lazy="joined",
    )

    @property
    def raw_model(self) -> Telemetry:
        return Telemetry(**self.raw)


class ProviderWalletHistoryModel(BaseModel):
    __tablename__ = "providers.wallet_history"

    provider_pubkey: Mapped[str] = mapped_column(
        ForeignKey("providers.pubkey"),
        primary_key=True,
    )
    date: Mapped[date] = mapped_column(primary_key=True)
    address: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    balance: Mapped[int] = mapped_column(BigInteger, nullable=False)
    earned: Mapped[int] = mapped_column(BigInteger, nullable=False)

    last_lt: Mapped[int] = mapped_column(BigInteger)

    __table_args__ = (
        Index("ix_wallet_history_provider_date", "provider_pubkey", "date"),
    )


class ProviderTrafficHistoryModel(BaseModel):
    __tablename__ = "providers.traffic_history"

    provider_pubkey: Mapped[str] = mapped_column(
        ForeignKey("providers.pubkey"),
        primary_key=True,
    )
    date: Mapped[date] = mapped_column(primary_key=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Bytes per day (integers for precision)
    traffic_in: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    traffic_out: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Last seen counters from telemetry; nullable for the very first sample
    last_bytes_recv: Mapped[t.Optional[int]] = mapped_column(BigInteger)
    last_bytes_sent: Mapped[t.Optional[int]] = mapped_column(BigInteger)

    __table_args__ = (
        Index("ix_traffic_history_provider_date", "provider_pubkey", "date"),
    )


class ProviderModel(BaseModel):
    __tablename__ = "providers"

    pubkey: Mapped[str] = mapped_column(String(64), primary_key=True)
    address: Mapped[str] = mapped_column(String(64), nullable=False)

    location: Mapped[t.Optional[dict[str, str]]] = mapped_column(JSON)
    status: Mapped[t.Optional[int]] = mapped_column(Integer)
    uptime: Mapped[float] = mapped_column(Float, nullable=False)
    working_time: Mapped[int] = mapped_column(BigInteger, nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    max_span: Mapped[int] = mapped_column(BigInteger, nullable=False)
    price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    min_span: Mapped[int] = mapped_column(BigInteger, nullable=False)
    max_bag_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reg_time: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_send_telemetry: Mapped[bool] = mapped_column(Boolean, nullable=False)

    raw: Mapped[t.Optional[dict]] = mapped_column(JSON)

    telemetry: Mapped[t.Optional[ProviderTelemetryModel]] = relationship(
        back_populates="provider",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="joined",
    )

    @property
    def raw_model(self) -> Provider:
        raw = self.raw.copy()

        if self.telemetry and self.telemetry.raw:
            raw["telemetry"] = self.telemetry.raw_model.model_dump()

        return Provider(**raw)

    @property
    def ui(self) -> ProviderUI:
        return ProviderUI(self)


class ProviderUI:
    def __init__(self, provider: ProviderModel) -> None:
        self.provider = provider

    @staticmethod
    def _format_or_dash(
        value: t.Optional[t.Union[float, int, str]],
        fmt: str = "{}",
        default: str = "N/A",
    ) -> str:
        if value is None:
            return default
        try:
            return fmt.format(value)
        except (Exception,):
            return default

    def _get_telemetry(self, field: str) -> t.Optional[t.Any]:
        return (
            getattr(self.provider.telemetry, field, None)
            if self.provider.telemetry
            else None
        )

    @property
    def short_pubkey(self) -> str:
        key = self.provider.pubkey
        return self._format_or_dash(f"{key[:5]}...{key[-6:]}" if key else None)

    @property
    def short_address(self) -> str:
        addr = self.provider.address
        return self._format_or_dash(f"{addr[:5]}...{addr[-6:]}" if addr else None)

    @property
    def location(self) -> str:
        loc = self.provider.location or {}
        country = loc.get("country")
        city = loc.get("city")

        location_str = ", ".join(part for part in [country, city] if part)
        return self._format_or_dash(location_str or None)

    @property
    def uptime(self) -> str:
        return self._format_or_dash(self.provider.uptime, "{:.2f}%")

    @property
    def price(self) -> str:
        price = self.provider.price
        return self._format_or_dash(price / 1e9 if price else None, "{:.2f} TON")

    @property
    def max_bag_size(self) -> str:
        size = self.provider.max_bag_size_bytes
        return self._format_or_dash(size / 1073741824 if size else None, "{:.2f} GB")

    @property
    def rating(self) -> str:
        return self._format_or_dash(self.provider.rating, "{:.2f}")

    @property
    def status_emoji(self) -> str:
        ratio = self.provider.uptime / 100 if self.provider.uptime else 0
        status = self.provider.status
        return {
            None: "⚪️",
            0: "🔴" if ratio < 0.8 else "🟡" if ratio < 0.99 else "🟢",
            2: "🟠",
            3: "🚫",
            500: "⚫️",
        }.get(status, "⚪️")

    @property
    def status_text(self) -> str:
        ratio = self.provider.uptime / 100 if self.provider.uptime else 0
        status = self.provider.status
        return {
            None: "No Data",
            0: "Unstable" if ratio < 0.8 else "Partial" if ratio < 0.99 else "Stable",
            2: "Invalid",
            3: "Not Store",
            500: "Not Accessible",
        }.get(status, "Unknown")

    @property
    def cpu_name(self) -> str:
        name = self._get_telemetry("cpu_name")
        return self._format_or_dash(name)

    @property
    def cpu_number(self) -> str:
        return self._format_or_dash(self._get_telemetry("cpu_number"), "{:.0f}")

    @property
    def cpu_is_virtual(self) -> str:
        value = self._get_telemetry("cpu_is_virtual")
        return "yes" if value else "no" if value is not None else "N/A"

    @property
    def ram(self) -> str:
        used = self._get_telemetry("usage_ram")
        total = self._get_telemetry("total_ram")
        return (
            f"{used:.2f}/{total:.2f} GB"
            if used is not None and total is not None
            else "N/A"
        )

    @property
    def storage(self) -> str:
        used = self._get_telemetry("used_provider_space")
        total = self._get_telemetry("total_provider_space")
        return (
            f"{used:.2f}/{total:.2f} GB"
            if used is not None and total is not None
            else "N/A"
        )

    @property
    def disk_read_speed(self) -> str:
        return self._format_or_dash(self._get_telemetry("qd64_disk_read_speed"))

    @property
    def disk_write_speed(self) -> str:
        return self._format_or_dash(self._get_telemetry("qd64_disk_write_speed"))

    @property
    def speed_download(self) -> str:
        val = self._get_telemetry("speedtest_download")
        if val is None:
            return "N/A"
        return f"{val / 1_000_000:.2f} Mbps"

    @property
    def speed_upload(self) -> str:
        val = self._get_telemetry("speedtest_upload")
        if val is None:
            return "N/A"
        return f"{val / 1_000_000:.2f} Mbps"

    @property
    def ping(self) -> str:
        return self._format_or_dash(self._get_telemetry("speedtest_ping"), "{:.2f} ms")

    @property
    def country(self) -> str:
        return self._format_or_dash(self._get_telemetry("country"))

    @property
    def isp(self) -> str:
        return self._format_or_dash(self._get_telemetry("isp"))

    @property
    def working_time(self) -> str:
        return self.provider.working_time or str(0)

    @property
    def reg_time(self) -> str:
        return self.provider.reg_time or str(0)

    @property
    def min_span(self) -> str:
        return self.provider.min_span or str(0)

    @property
    def max_span(self) -> str:
        return self.provider.max_span or str(0)

    @property
    def storage_git_hash(self) -> str:
        return self._format_or_dash(self._get_telemetry("storage_git_hash"))

    @property
    def provider_git_hash(self) -> str:
        return self._format_or_dash(self._get_telemetry("provider_git_hash"))
