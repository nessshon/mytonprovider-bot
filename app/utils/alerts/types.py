import typing as t
from dataclasses import dataclass
from datetime import date
from enum import Enum

from ...database.models import ProviderModel


class AlertTypes(str, Enum):
    MONTHLY_REPORT = "monthly_report"
    SERVICE_RESTARTED = "service_restarted"

    CPU_HIGH = "cpu_high"
    RAM_HIGH = "ram_high"
    NETWORK_HIGH = "network_high"
    DISK_LOAD_HIGH = "disk_load_high"
    DISK_SPACE_LOW = "disk_space_low"


class AlertStages(str, Enum):
    DETECTED = "detected"
    RESOLVED = "resolved"
    INFO = "info"


@dataclass
class MonthlyReport:
    period: str
    start_date: date
    end_date: date
    used_space_bytes: int
    total_space_bytes: int
    used_space_eom_bytes: int
    traffic_in_bytes: int
    traffic_out_bytes: int
    earned_nanoton: int
    provider: ProviderModel


ServiceRestartedAlert = tuple[AlertTypes, dict[str, t.Any]]
