from __future__ import annotations

import math
import typing as t

from .types import AlertTypes, ServiceRestartedAlert
from ...database.models import ProviderModel, TelemetryModel

DEFAULT_THRESHOLDS: dict[str, float] = {
    AlertTypes.CPU_HIGH.value: 90.0,  # percent of core capacity
    AlertTypes.RAM_HIGH.value: 90.0,  # percent
    AlertTypes.NETWORK_HIGH.value: 90.0,  # percent of link capacity
    AlertTypes.DISK_LOAD_HIGH.value: 90.0,  # percent
    AlertTypes.DISK_SPACE_LOW.value: 90.0,  # percent used
}


def _is_num(x: t.Any) -> bool:
    if not isinstance(x, (int, float)):
        return False
    return math.isfinite(float(x))


class OverloadDetector:
    """
    Stateless detector operating on a single telemetry snapshot.

    Notes:
      - CPU uses load average (1m preferred) normalized to percent of CPU cores:
        pct = (loadavg_1m / cpu_count) * 100.0
      - Thresholds are user-configurable. We DO NOT clamp thresholds to 100, since
        loadavg percent may legitimately exceed 100% (e.g., 2.0 * cpu_count == 200%).
    """

    def __init__(
        self,
        provider: ProviderModel,
        telemetry: TelemetryModel,
        thresholds: t.Optional[t.Mapping[str, float]] = None,
    ) -> None:
        self.provider = provider
        self.telemetry = telemetry

        # Merge user thresholds over defaults; invalid values are ignored.
        self._thresholds: dict[str, float] = dict(DEFAULT_THRESHOLDS)
        if thresholds:
            for k, v in thresholds.items():
                try:
                    self._thresholds[str(k)] = float(v)
                except (TypeError, ValueError):
                    continue

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

    def cpu_percent(self) -> t.Optional[float]:
        """
        Returns CPU usage as percent of total core capacity based on loadavg.
        Example: 200.0 means loadavg_1m == 2.0 * cpu_count.
        """
        cpu_info = self.telemetry.cpu_info or {}
        loads = cpu_info.get("cpu_load", [])
        count = cpu_info.get("cpu_count", 1)

        if not isinstance(loads, list) or not _is_num(count) or float(count) <= 0:
            return None

        # Prefer 1-minute window; fallback to max if missing or invalid
        raw: t.Optional[float] = None
        try:
            raw = float(loads[0])
        except (Exception,):
            nums = [float(x) for x in loads if _is_num(x)]
            if nums:
                raw = max(nums)

        if raw is None:
            return None

        count_f = float(count)
        return (raw / count_f) * 100.0

    def is_cpu_high(self) -> bool:
        """Check 'enter overload' condition (>= thr_on)."""
        thr_on = self._thr(AlertTypes.CPU_HIGH)
        pct = self.cpu_percent()
        return pct is not None and pct >= thr_on

    def is_ram_high(self) -> bool:
        ram = self.telemetry.ram or {}
        usage = ram.get("usage_percent")
        thr = self._thr(AlertTypes.RAM_HIGH)
        return _is_num(usage) and float(usage) >= thr

    def is_disk_space_low(self) -> bool:
        storage = self.telemetry.storage or {}
        p = storage.get("provider") or {}

        used = p.get("used_provider_space")
        total = p.get("total_provider_space")

        # Fallback to whole disk if provider section absent.
        if not (_is_num(used) and _is_num(total)):
            used = storage.get("used_disk_space", 0.0)
            total = storage.get("total_disk_space", 1.0)

        thr = self._thr(AlertTypes.DISK_SPACE_LOW)
        if not (_is_num(used) and _is_num(total)) or float(total) <= 0:
            return False

        usage_percent = float(used) / float(total) * 100.0
        return usage_percent >= thr

    def is_disk_load_high(self) -> bool:
        loads_dict = self.telemetry.disks_load_percent or {}
        thr = self._thr(AlertTypes.DISK_LOAD_HIGH)
        if not isinstance(loads_dict, dict):
            return False

        for loads in loads_dict.values():
            if not isinstance(loads, list):
                continue
            vals = [float(x) for x in loads if _is_num(x)]
            if any(x >= thr for x in vals):
                return True
        return False

    def is_network_high(self) -> bool:
        net_load = self.telemetry.net_load or []
        thr = self._thr(AlertTypes.NETWORK_HIGH)
        if not isinstance(net_load, list):
            return False

        vals = [float(x) for x in net_load if _is_num(x)]
        if not vals:
            return False

        link_mbit = self._link_mbit()
        if link_mbit <= 0:
            return False

        # net_load likely MB/s -> Mbit/s
        max_usage_mbit = max(vals) * 8.0
        usage_percent = (max_usage_mbit / link_mbit) * 100.0
        return usage_percent >= thr

    def _thr(self, key: AlertTypes) -> float:
        """Return user threshold; lower-bounded by 0, NOT capped by 100."""
        val = self._thresholds.get(key.value, DEFAULT_THRESHOLDS[key.value])
        try:
            v = float(val)
        except (TypeError, ValueError):
            v = float(DEFAULT_THRESHOLDS[key.value])
        return 0.0 if v < 0.0 else v

    def _link_mbit(self) -> float:
        # Provider.speedtest_* are in bytes/sec; convert to Mbit/s (1 Mbit = 125_000 bytes).
        prov_tel = getattr(self.provider, "telemetry", None)
        down_bps = getattr(prov_tel, "speedtest_download", None)
        up_bps = getattr(prov_tel, "speedtest_upload", None)

        candidates: list[float] = []
        for c in (down_bps, up_bps):
            if _is_num(c) and float(c) > 0:
                candidates.append(float(c))

        if not candidates:
            return 0.0

        return max(candidates) / 125_000.0


class ServiceRestartedDetector:

    @staticmethod
    def _to_uptime(x: t.Any) -> t.Optional[int]:
        try:
            v = int(x)
            return v if v >= 0 else None
        except (Exception,):
            return None

    @staticmethod
    def _detect_restart(
        prev_uptime: t.Optional[int],
        curr_uptime: t.Optional[int],
    ) -> bool:
        if prev_uptime is None or curr_uptime is None:
            return False
        return curr_uptime < prev_uptime

    def get_triggered_alerts(
        self,
        prev_telemetry: t.Optional[TelemetryModel],
        curr_telemetry: t.Optional[TelemetryModel],
    ) -> list[ServiceRestartedAlert]:
        if prev_telemetry is None or curr_telemetry is None:
            return []

        def g(obj: t.Any, *path: str) -> t.Any:
            for p in path:
                obj = getattr(obj, p, None) if not isinstance(obj, dict) else obj.get(p)
                if obj is None:
                    return None
            return obj

        prev_mtp_uptime = self._to_uptime(
            g(prev_telemetry.storage, "provider", "service_uptime")
        )
        curr_mtp_uptime = self._to_uptime(
            g(curr_telemetry.storage, "provider", "service_uptime")
        )

        prev_ts_uptime = self._to_uptime(g(prev_telemetry.storage, "service_uptime"))
        curr_ts_uptime = self._to_uptime(g(curr_telemetry.storage, "service_uptime"))

        alerts: list[ServiceRestartedAlert] = []
        if self._detect_restart(prev_mtp_uptime, curr_mtp_uptime):
            alerts.append(
                (AlertTypes.SERVICE_RESTARTED, {"service_name": "mytonproviderd"})
            )
        if self._detect_restart(prev_ts_uptime, curr_ts_uptime):
            alerts.append(
                (AlertTypes.SERVICE_RESTARTED, {"service_name": "ton-storage"})
            )

        return alerts
