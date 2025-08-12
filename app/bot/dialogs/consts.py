from app.utils.alerts import AlertTypes

PROVIDER_TABS = [
    "hardware",
    "storage",
    "benchmarks",
    "network",
    "software",
    "wallet",
]
DEFAULT_PROVIDER_TAB = "hardware"

ALERT_TABS = [
    "types",
    "thresholds",
]
DEFAULT_ALERT_TAB = "types"

STEP_LEFT = [("m10", "−10"), ("m5", "−5"), ("m1", "−1")]
STEP_RIGHT = [("p1", "+1"), ("p5", "+5"), ("p10", "+10")]

DEFAULT_MIN = 30
DEFAULT_MAX = 100

LIMITS = {
    AlertTypes.CPU_HIGH: (DEFAULT_MIN, DEFAULT_MAX),
    AlertTypes.RAM_HIGH: (DEFAULT_MIN, DEFAULT_MAX),
    AlertTypes.NETWORK_HIGH: (DEFAULT_MIN, DEFAULT_MAX),
    AlertTypes.DISK_LOAD_HIGH: (DEFAULT_MIN, DEFAULT_MAX),
    AlertTypes.DISK_SPACE_LOW: (DEFAULT_MIN, DEFAULT_MAX),
}
