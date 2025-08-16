import typing as t

from pydantic import BaseModel as PydanticBaseModel, Field
from pydantic import ConfigDict


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(extra="ignore")


class ProviderInfo(BaseModel):
    pubkey: str
    used_provider_space: float
    total_provider_space: float
    max_bag_size_bytes: int
    service_uptime: t.Optional[int] = None


class StorageInfo(BaseModel):
    pubkey: str
    disk_name: t.Optional[str] = None
    total_disk_space: t.Optional[float] = None
    used_disk_space: t.Optional[float] = None
    free_disk_space: t.Optional[float] = None
    provider: ProviderInfo
    service_uptime: t.Optional[int] = None


class MemoryInfo(BaseModel):
    total: float
    usage: float
    usage_percent: float


class UnameInfo(BaseModel):
    sysname: str
    release: str
    version: str
    machine: str


class CPUInfo(BaseModel):
    cpu_load: t.List[float]
    cpu_count: int
    cpu_name: str
    product_name: str
    is_virtual: bool


class TelemetryRequest(BaseModel):
    storage: StorageInfo
    git_hashes: t.Dict[str, t.Optional[str]] = Field(default_factory=dict)

    net_load: t.Optional[t.List[t.Optional[float]]] = None
    disks_load: t.Optional[t.Dict[str, t.List[t.Optional[float]]]] = None
    disks_load_percent: t.Optional[t.Dict[str, t.List[t.Optional[float]]]] = None
    iops: t.Optional[t.Dict[str, t.List[t.Optional[float]]]] = None
    pps: t.Optional[t.List[t.Optional[float]]] = None

    ram: t.Optional[MemoryInfo] = None
    swap: t.Optional[MemoryInfo] = None
    uname: t.Optional[UnameInfo] = None
    cpu_info: t.Optional[CPUInfo] = None
    pings: t.Optional[t.Dict[str, float]] = None
    bytes_recv: t.Optional[int] = None
    bytes_sent: t.Optional[int] = None
    net_recv: t.Optional[t.List[t.Optional[float]]] = None
    net_sent: t.Optional[t.List[t.Optional[float]]] = None
    telemetry_pass: t.Optional[str] = None
    timestamp: t.Optional[int] = None


class TelemetryResponse(BaseModel):
    providers: t.List[TelemetryRequest]


class Telemetry(BaseModel):
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
    speedtest_download: t.Optional[int] = None
    speedtest_upload: t.Optional[int] = None
    speedtest_ping: t.Optional[float] = None
    cpu_number: t.Optional[int] = None
    cpu_is_virtual: t.Optional[bool] = None


class Location(BaseModel):
    country: t.Optional[str] = None
    country_iso: t.Optional[str] = None
    city: t.Optional[str] = None
    time_zone: t.Optional[str] = None


class Provider(BaseModel):
    location: t.Optional[Location] = None
    status: t.Optional[int] = None
    pubkey: str
    address: str
    uptime: float
    working_time: int
    rating: float
    max_span: int
    price: int
    min_span: int
    max_bag_size_bytes: int
    reg_time: int
    is_send_telemetry: bool
    telemetry: Telemetry


class ProvidersResponse(BaseModel):
    providers: t.List[Provider]


class ProviderSearchPayload(BaseModel):
    limit: int = 100
    offset: int = 0
