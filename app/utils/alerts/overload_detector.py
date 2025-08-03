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
        cpu_info = self.telemetry.cpu_info or {}
        cpu_load = cpu_info.get("cpu_load", [])
        cpu_count = cpu_info.get("cpu_count", 1)
        threshold_percent = self.thresholds.cpu_percent

        if not isinstance(cpu_load, list):
            return False
        if not isinstance(cpu_count, (int, float)) or cpu_count <= 0:
            return False

        filtered = [load for load in cpu_load if isinstance(load, (int, float))]
        if not filtered:
            return False

        return any((load / cpu_count) * 100 > threshold_percent for load in filtered)

    def is_ram_high(self) -> bool:
        ram = self.telemetry.ram or {}
        usage = ram.get("usage_percent")
        threshold_percent = self.thresholds.ram_percent

        if isinstance(usage, (int, float)):
            if usage > threshold_percent:
                return True

        return False

    def is_disk_space_low(self) -> bool:
        storage = self.telemetry.storage or {}
        used = storage.get("used_disk_space", 0.0)
        total = storage.get("total_disk_space", 1.0)
        threshold_percent = self.thresholds.disk_space_percent

        if (
            not isinstance(used, (int, float))
            or not isinstance(total, (int, float))
            or total <= 0
        ):
            return False

        usage_percent = (used / total) * 100
        return usage_percent > threshold_percent

    def is_disk_load_high(self) -> bool:
        loads_dict = self.telemetry.disks_load_percent or {}
        threshold_percent = self.thresholds.disk_load_percent

        if not isinstance(loads_dict, dict):
            return False

        for loads in loads_dict.values():
            if not isinstance(loads, list):
                continue
            filtered = [load for load in loads if isinstance(load, (int, float))]
            if any(load > threshold_percent for load in filtered):
                return True

        return False

    def is_network_high(self) -> bool:
        net_load = self.telemetry.net_load or []
        threshold_percent = self.thresholds.network_percent

        if not isinstance(net_load, list):
            return False

        filtered = [load for load in net_load if isinstance(load, (int, float))]
        if not filtered:
            return False

        speed_bytes = self.provider.telemetry.speedtest_download
        if not isinstance(speed_bytes, (int, float)) or speed_bytes <= 0:
            return False

        speed_mbit = speed_bytes / 125_000
        max_usage = max(filtered, default=0.0)
        usage_percent = (max_usage / speed_mbit) * 100

        return usage_percent > threshold_percent
