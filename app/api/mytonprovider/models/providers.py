import typing as t
from typing import Any

from .base import BaseModel


class LocationInfo(BaseModel):
    country: t.Optional[str] = None
    country_iso: t.Optional[str] = None
    city: t.Optional[str] = None
    time_zone: t.Optional[str] = None


class TelemetryInfo(BaseModel):
    storage_git_hash: t.Optional[str] = None
    provider_git_hash: t.Optional[str] = None
    qd64_disk_read_speed: t.Optional[str] = None
    qd64_disk_write_speed: t.Optional[str] = None
    country: t.Optional[str] = None
    isp: t.Optional[str] = None
    cpu_name: t.Optional[str] = None
    updated_at: t.Optional[int] = None
    total_provider_space: t.Optional[float] = None
    used_provider_space: t.Optional[float] = None
    total_ram: t.Optional[float] = None
    usage_ram: t.Optional[float] = None
    ram_usage_percent: t.Optional[float] = None
    speedtest_download: t.Optional[t.Union[int, float]] = None
    speedtest_upload: t.Optional[t.Union[int, float]] = None
    speedtest_ping: t.Optional[float] = None
    cpu_number: t.Optional[int] = None
    cpu_is_virtual: t.Optional[bool] = None

    def model_post_init(self, context: Any, /) -> None:
        if isinstance(self.speedtest_upload, float):
            self.speedtest_upload = int(self.speedtest_upload)
        if isinstance(self.speedtest_download, float):
            self.speedtest_download = int(self.speedtest_download)


class Provider(BaseModel):
    location: t.Optional[LocationInfo] = None
    status: t.Optional[int] = None
    pubkey: str
    address: str
    uptime: float
    status_ratio: t.Optional[float] = None
    working_time: int
    rating: float
    max_span: int
    price: int
    min_span: int
    max_bag_size_bytes: int
    reg_time: int
    is_send_telemetry: bool
    telemetry: TelemetryInfo


class ProvidersResponse(BaseModel):
    providers: t.List[Provider]


class ProviderSearchPayload(BaseModel):
    limit: int = 100
    offset: int = 0
