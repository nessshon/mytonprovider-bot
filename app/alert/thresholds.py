import typing as t

from .types import AlertTypes

THRESHOLDS: t.Dict[str, float] = {
    AlertTypes.CPU_HIGH.value: 90.0,
    AlertTypes.RAM_HIGH.value: 90.0,
    AlertTypes.NETWORK_HIGH.value: 90.0,
    AlertTypes.DISK_LOAD_HIGH.value: 90.0,
    AlertTypes.DISK_SPACE_LOW.value: 90.0,
    AlertTypes.PROVIDER_OFFLINE.value: 15 * 60,
}
