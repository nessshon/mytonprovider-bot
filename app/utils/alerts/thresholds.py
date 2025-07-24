from dataclasses import dataclass


@dataclass
class OverloadThresholds:
    cpu_percent: float = 90
    ram_percent: float = 90
    network_percent: float = 90
    disk_load_percent: float = 80
    disk_space_percent: float = 90
