from enum import Enum


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
