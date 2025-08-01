import typing as t

from pydantic import BaseModel


class ProviderInfo(BaseModel):
    pubkey: str
    used_provider_space: float
    total_provider_space: float
    max_bag_size_bytes: int


class StorageInfo(BaseModel):
    pubkey: str
    disk_name: str
    total_disk_space: float
    used_disk_space: float
    free_disk_space: float
    provider: ProviderInfo


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


class BenchmarkLevel(BaseModel):
    read_speed: t.Optional[float] = None
    write_speed: t.Optional[float] = None
    read_iops: t.Optional[float] = None
    write_iops: t.Optional[float] = None
    random_ops: t.Optional[float] = None


class BenchmarkInfo(BaseModel):
    lite: BenchmarkLevel
    hard: BenchmarkLevel
    full: BenchmarkLevel


class TelemetryRequest(BaseModel):
    storage: StorageInfo
    git_hashes: t.Dict[str, str]
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
    benchmark: t.Optional[BenchmarkInfo] = None
    x_real_ip: str


class TelemetryResponse(BaseModel):
    providers: t.List[TelemetryRequest]


class Telemetry(BaseModel):
    storage_git_hash: t.Optional[str]
    provider_git_hash: t.Optional[str]
    qd64_disk_read_speed: t.Optional[str]
    qd64_disk_write_speed: t.Optional[str]
    country: t.Optional[str]
    isp: t.Optional[str]
    cpu_name: t.Optional[str]
    updated_at: t.Optional[int]
    total_provider_space: t.Optional[float]
    used_provider_space: t.Optional[float]
    total_ram: t.Optional[float]
    usage_ram: t.Optional[float]
    ram_usage_percent: t.Optional[float]
    speedtest_download: t.Optional[int]
    speedtest_upload: t.Optional[int]
    speedtest_ping: t.Optional[float]
    cpu_number: t.Optional[int]
    cpu_is_virtual: t.Optional[bool]


class Location(BaseModel):
    country: t.Optional[str]
    country_iso: t.Optional[str]
    city: t.Optional[str]
    time_zone: t.Optional[str]


class Provider(BaseModel):
    location: t.Optional[Location]
    status: t.Optional[int]
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
