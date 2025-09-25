import typing as t

from pydantic import Field

from .base import BaseModel


class CPUInfo(BaseModel):
    cpu_count: t.Optional[int] = None
    cpu_load: t.Optional[t.List[float]] = None
    cpu_name: t.Optional[str] = None
    is_virtual: t.Optional[bool] = None
    product_name: t.Optional[str] = None


class RamInfo(BaseModel):
    total: float
    usage: float
    usage_percent: float


class ProviderInfo(BaseModel):
    max_bag_size_bytes: int
    pubkey: str
    service_uptime: t.Optional[int] = None
    total_provider_space: float
    used_provider_space: float


class StorageInfo(BaseModel):
    disk_name: t.Optional[str] = None
    free_disk_space: t.Optional[float] = None
    provider: ProviderInfo
    pubkey: str
    service_uptime: t.Optional[int] = None
    total_disk_space: t.Optional[float] = None
    used_disk_space: t.Optional[float] = None


class UnameInfo(BaseModel):
    machine: t.Optional[str] = None
    release: t.Optional[str] = None
    sysname: t.Optional[str] = None
    version: t.Optional[str] = None


class Telemetry(BaseModel):
    bytes_recv: t.Optional[int] = None
    bytes_sent: t.Optional[int] = None
    cpu_info: t.Optional[CPUInfo] = None
    disks_load: t.Optional[t.Dict[str, t.List[t.Optional[float]]]] = None
    disks_load_percent: t.Optional[t.Dict[str, t.List[t.Optional[float]]]] = None
    git_hashes: t.Dict[str, t.Optional[str]] = Field(default_factory=dict)
    iops: t.Optional[t.Dict[str, t.List[t.Optional[float]]]] = None
    net_load: t.Optional[t.List[t.Optional[float]]] = None
    net_recv: t.Optional[t.List[t.Optional[float]]] = None
    net_sent: t.Optional[t.List[t.Optional[float]]] = None
    pings: t.Optional[t.Dict[str, float]] = None
    pps: t.Optional[t.List[t.Optional[float]]] = None
    ram: t.Optional[RamInfo] = None
    storage: StorageInfo
    swap: t.Optional[RamInfo] = None
    telemetry_pass: t.Optional[str] = None
    timestamp: t.Optional[int] = None
    uname: t.Optional[UnameInfo] = None


class TelemetryResponse(BaseModel):
    providers: t.List[Telemetry]
