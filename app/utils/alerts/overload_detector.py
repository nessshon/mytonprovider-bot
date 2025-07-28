import typing as t

from .thresholds import OverloadThresholds
from .types import AlertTypes
from ...database.models import (
    ProviderModel,
    TelemetryModel,
)


class OverloadDetector:

    def __init__(
        self,
        provider: ProviderModel,
        telemetry: TelemetryModel,
        thresholds: OverloadThresholds = OverloadThresholds(),
    ) -> None:
        self.provider = provider
        self.telemetry = telemetry
        self.thresholds = thresholds

    def get_triggered_alerts(self) -> t.Set[AlertTypes]:
        alerts: list[AlertTypes] = []

        if self.is_cpu_high():
            alerts.append(AlertTypes.CPU_HIGH)

        if self.is_ram_high():
            alerts.append(AlertTypes.RAM_HIGH)

        if self.is_disk_space_low():
            alerts.append(AlertTypes.DISK_SPACE_LOW)

        if self.is_disk_load_high():
            alerts.append(AlertTypes.DISK_LOAD_HIGH)

        if self.is_network_high():
            alerts.append(AlertTypes.NETWORK_HIGH)

        return set(alerts)

    def is_cpu_high(self) -> bool:
        cpu_load = self.telemetry.cpu_info.get("cpu_load", [])
        cpu_count = self.telemetry.cpu_info.get("cpu_count", 1)
        return any(
            (load / cpu_count) * 100 > self.thresholds.cpu_percent for load in cpu_load
        )

    def is_ram_high(self) -> bool:
        ram_usage_percent = self.telemetry.ram.get("usage_percent")
        return (
            ram_usage_percent is not None
            and ram_usage_percent > self.thresholds.ram_percent
        )

    def is_disk_space_low(self) -> bool:
        used = self.telemetry.storage.get("used_disk_space", 0.0)
        total = self.telemetry.storage.get("total_disk_space", 1.0)
        usage_percent = (used / total) * 100
        return usage_percent > self.thresholds.disk_space_percent

    def is_disk_load_high(self) -> bool:
        disk_load_percent = self.telemetry.disks_load_percent or {}
        for loads in disk_load_percent.values():
            if any(load > self.thresholds.disk_load_percent for load in loads):
                return True
        return False

    def is_network_high(self) -> bool:
        net_load = self.telemetry.net_load or []
        speed_bytes = self.provider.telemetry.speedtest_download

        if speed_bytes is None or speed_bytes == 0:
            return False

        speed_mbit = speed_bytes / 125_000
        max_usage = max(net_load, default=0.0)
        usage_percent = (max_usage / speed_mbit) * 100

        return usage_percent > self.thresholds.network_percent
