import os
import time
import typing as t
from contextlib import suppress

from .thresholds import THRESHOLDS
from .types import AlertTypes
from ..api.mytonprovider import CPUInfo, RamInfo, StorageInfo
from ..database.models import ProviderModel, TelemetryModel, TelemetryHistoryModel


class AlertDetector:

    def __init__(
        self,
        provider: ProviderModel,
        telemetry: TelemetryModel,
        telemetry_history: t.Optional[TelemetryHistoryModel] = None,
        user_thresholds: t.Optional[t.Mapping[str, float]] = None,
    ) -> None:
        self.provider = provider
        self.telemetry = telemetry
        self.telemetry_history = telemetry_history

        # Merge user thresholds over defaults (copy to avoid mutating global defaults)
        self.thresholds: dict[str, float] = dict(THRESHOLDS)
        if user_thresholds is not None:
            for alert_type, threshold in user_thresholds.items():
                with suppress(Exception):
                    self.thresholds[alert_type] = float(threshold)

    def get_triggered_base_alerts(self) -> t.Set[t.Union[AlertTypes, str]]:
        """Return set of base alerts triggered.

        Example output:
            {AlertTypes.CPU_HIGH, AlertTypes.RAM_HIGH}
        """
        triggered = []

        if self.is_cpu_high():
            triggered.append(AlertTypes.CPU_HIGH)
        if self.is_ram_high():
            triggered.append(AlertTypes.RAM_HIGH)
        if self.is_network_high():
            triggered.append(AlertTypes.NETWORK_HIGH)
        if self.is_disk_load_high():
            triggered.append(AlertTypes.DISK_LOAD_HIGH)
        if self.is_disk_space_low():
            triggered.append(AlertTypes.DISK_SPACE_LOW)
        if self.is_provider_offline():
            triggered.append(AlertTypes.PROVIDER_OFFLINE)

        return set(triggered)

    def get_triggered_service_alerts(
        self,
    ) -> t.List[t.Tuple[AlertTypes, t.Dict[str, t.Any]]]:
        """Return service alerts (restarts).

        Example output:
        [
            (AlertTypes.SERVICE_RESTARTED, {"service_name": "ton-storage"}),
            (AlertTypes.SERVICE_RESTARTED, {"service_name": "ton-storage-provider"})
        ]
        """
        triggered = []

        if self.is_ton_storage_restrated():
            payload = {"service_name": "ton-storage"}
            triggered.append((AlertTypes.SERVICE_RESTARTED, payload))
        if self.is_ton_storage_provider_restrated():
            payload = {"service_name": "ton-storage-provider"}
            triggered.append((AlertTypes.SERVICE_RESTARTED, payload))

        return triggered

    @classmethod
    def diff_alerts(
        cls,
        triggered: set[AlertTypes],
        enabled: set[AlertTypes],
        active: set[AlertTypes],
    ) -> tuple[set[AlertTypes], set[AlertTypes]]:
        """Diff triggered alerts vs active ones.

        Example:
            triggered = {CPU_HIGH, RAM_HIGH}
            enabled = {CPU_HIGH, RAM_HIGH}
            active = {CPU_HIGH}
            => ({"RAM_HIGH"}, set())  # detected, resolved
        """
        triggered_enabled = triggered & enabled
        detected = triggered_enabled - active
        resolved = (active & enabled) - triggered
        return detected, resolved

    def is_cpu_high(self) -> bool:
        """High when 5m load exceeds (CPU_HIGH% of cores).

        Example telemetry.cpu_info:
        {
            "cpu_count": 8,
            "cpu_load": [6.5, 5.8, 3.2]  # [1m, 5m, 15m]
        }
        """
        if not self.telemetry.cpu_info:
            return False

        cpu_info = CPUInfo(**self.telemetry.cpu_info)
        if not cpu_info.cpu_load or not cpu_info.cpu_count:
            return False
        if len(cpu_info.cpu_load) < 2:
            return False

        load5 = cpu_info.cpu_load[1]  # 5m load average
        cores = max(1, cpu_info.cpu_count)  # guard against zero

        cpu_load_percent = float(load5 / cores * 100)
        thr_ratio = float(self.thresholds[AlertTypes.CPU_HIGH])
        return cpu_load_percent > thr_ratio

    def is_ram_high(self) -> bool:
        """High when RAM usage_percent >= RAM_HIGH threshold (in percent).

        Example telemetry.ram:
        {
            "usage_percent": 82.3
        }
        """
        if self.telemetry.ram is None:
            return False

        ram = RamInfo(**self.telemetry.ram)
        if ram.usage_percent is None:
            return False

        thr_percent = float(self.thresholds[AlertTypes.RAM_HIGH])
        return ram.usage_percent >= thr_percent

    def is_network_high(self) -> bool:
        """
        High when network load (in %) >= NETWORK_HIGH.
        Prefer total net_load[1m]; if missing, use max(recv[1m], sent[1m]).

        Example telemetry:
        {
            "net_load": [0.72, 0.50, 0.30]
            "net_recv": [0.55, 0.40, 0.25],
            "net_sent": [0.20, 0.10, 0.05]
        }
        """
        thr = float(self.thresholds[AlertTypes.NETWORK_HIGH])
        cap = getattr(self.telemetry, "iface_capacity_mbps", None)
        if not cap or cap <= 0:
            return False  # no capacity → don't fire

        # MB/s → Mbps (*8), then to %
        mb_s = [
            _first_slot(getattr(self.telemetry, "net_load", None)),
            _first_slot(getattr(self.telemetry, "net_recv", None)),
            _first_slot(getattr(self.telemetry, "net_sent", None)),
        ]
        mbps = [v * 8.0 for v in mb_s if v is not None]
        if not mbps:
            return False

        pct = (max(mbps) / cap) * 100.0
        return pct >= thr

    def is_disk_load_high(self) -> bool:
        """
        High when disk load (1m slot) >= DISK_LOAD_HIGH.

        Example telemetry.disks_load_percent:
        {
            "nvme0n1": [73.5, 60.2, 50.1],
            "sda": [40.0, 35.2, 30.0]
        }
        """
        disks_loads = self.telemetry.disks_load_percent
        if not isinstance(disks_loads, dict) or not disks_loads:
            return False

        storage = getattr(self.telemetry, "storage", None)
        disk_name = None

        if isinstance(storage, dict) and storage.get("disk_name"):
            disk_name = os.path.basename(storage.get("disk_name"))
        if not disk_name or disk_name not in disks_loads:
            disk_name = next(iter(disks_loads.keys()))

        values = disks_loads.get(disk_name)
        if not isinstance(values, (list, tuple)) or len(values) < 3:
            return False

        disk_load_percent = float(values[2])
        thr_percent = float(self.thresholds[AlertTypes.DISK_LOAD_HIGH])
        return disk_load_percent > thr_percent

    def is_disk_space_low(self) -> bool:
        """
        Low space when usage% >= DISK_SPACE_LOW.

        Example telemetry.storage:
        {
            "provider": {
                "used_provider_space": 850000000000,
                "total_provider_space": 1000000000000
            }
        }
        """
        if self.telemetry.storage is None:
            return False

        storage = StorageInfo(**self.telemetry.storage)
        if (
            not storage.provider.used_provider_space
            or not storage.provider.total_provider_space
        ):
            return False

        used = float(storage.provider.used_provider_space)
        total = float(storage.provider.total_provider_space)
        if total <= 0:
            return False

        prov_usage = (used / total) * 100.0
        thr_percent = float(self.thresholds[AlertTypes.DISK_SPACE_LOW])
        return prov_usage >= thr_percent

    def is_provider_offline(self) -> bool:
        """
        Determine if provider is offline.

        Logic:
          - Provider considered offline if telemetry data is too old (no updates within 30 min)
            and provider is not marked as stable.
          - Stability is defined by: status == 0 and status_ratio >= 0.99.

        Example:
            telemetry.timestamp = 1727171727  # Last telemetry update
            provider.status = 1               # Not stable
            provider.status_ratio = 0.80      # 80% uptime in period
        """
        # No telemetry timestamp → cannot assert offline
        if self.telemetry.timestamp is None:
            return False

        age_sec = int(time.time()) - int(self.telemetry.timestamp)
        # Telemetry is fresh (≤ 30 min) — still considered online
        if age_sec <= THRESHOLDS[AlertTypes.PROVIDER_OFFLINE]:  # 30 min
            return False
        # Stable → not offline
        if self.provider.status == 0 and self.provider.status_ratio >= 0.99:
            return False
        return True

    def is_ton_storage_provider_restrated(self) -> bool:
        """Detect restart if provider.service_uptime decreased.

        Example:
            telemetry.storage = {"provider": {"service_uptime": 1200}}
            telemetry_history.storage = {"provider": {"service_uptime": 3000}}
        """
        if self.telemetry_history is None:
            return False
        if self.telemetry_history.storage is None or self.telemetry.storage is None:
            return False

        storage = StorageInfo(**self.telemetry.storage)
        prev_storage = StorageInfo(**self.telemetry_history.storage)

        curr_uptime = storage.provider.service_uptime
        prev_uptime = prev_storage.provider.service_uptime
        if not curr_uptime or not prev_uptime:
            return False
        return curr_uptime < prev_uptime

    def is_ton_storage_restrated(self) -> bool:
        """Detect restart if storage.service_uptime decreased.

        Example:
            telemetry.storage = {"service_uptime": 12345}
            telemetry_history.storage = {"service_uptime": 45678}
        """
        if self.telemetry_history is None:
            return False
        if self.telemetry.storage is None or self.telemetry_history.storage is None:
            return False

        storage = StorageInfo(**self.telemetry.storage)
        prev_storage = StorageInfo(**self.telemetry_history.storage)

        curr_uptime = storage.service_uptime
        prev_uptime = prev_storage.service_uptime
        if not curr_uptime or not prev_uptime:
            return False
        return curr_uptime < prev_uptime


def _first_slot(arr: t.Optional[t.Sequence[float]]) -> t.Optional[float]:
    """Return the 1m value if available; otherwise fall back to 5m/15m."""
    if not arr:
        return None
    for i in (1, 0, 2):
        with suppress(Exception):
            v = arr[i]
            if v is not None:
                return float(v)
    return None


def _to_percent(v: t.Optional[float]) -> t.Optional[float]:
    """
    Normalize a value to percent:
    - If it's a ratio (0..1), convert to percent.
    - If it's already percent (>=1), return as is.
    """
    if v is None:
        return None
    return v * 100.0 if v <= 1.0 else v
