import typing as t

if t.TYPE_CHECKING:
    from ...database.models.provider import BaseProviderModel
else:
    BaseProviderModel = t.Any


class ProviderUI:

    def __init__(self, provider: BaseProviderModel) -> None:
        self.provider = provider

    @staticmethod
    def _format_or_dash(
        value: t.Optional[t.Union[float, int, str]],
        fmt: str = "{}",
        default: str = "N/A",
    ) -> str:
        if value is None:
            return default
        try:
            return fmt.format(value)
        except (Exception,):
            return default

    def _get_ratio(self) -> float:
        r = self.provider.status_ratio
        if r is None:
            return 0.0
        try:
            r = float(r)
        except (TypeError, ValueError):
            return 0.0
        if r < 0.0:
            r = 0.0
        if r > 1.0:
            r = 1.0
        return r

    @property
    def short_pubkey(self) -> str:
        key = self.provider.pubkey
        return self._format_or_dash(f"{key[:5]}...{key[-6:]}" if key else None)

    @property
    def short_address(self) -> str:
        addr = self.provider.address
        return self._format_or_dash(f"{addr[:5]}...{addr[-6:]}" if addr else None)

    @property
    def location(self) -> str:
        loc = self.provider.location or {}
        country = loc.get("country")
        city = loc.get("city")

        location_str = ", ".join(part for part in [country, city] if part)
        return self._format_or_dash(location_str or None)

    @property
    def uptime(self) -> str:
        return self._format_or_dash(self.provider.uptime, "{:.2f}%")

    @property
    def price(self) -> str:
        price = self.provider.price
        return self._format_or_dash(price / 1e9 if price else None, "{:.2f} TON")

    @property
    def max_bag_size(self) -> str:
        size = self.provider.max_bag_size_bytes
        return self._format_or_dash(size / 1073741824 if size else None, "{:.2f} GB")

    @property
    def rating(self) -> str:
        return self._format_or_dash(self.provider.rating, "{:.2f}")

    @property
    def cpu_name(self) -> str:
        name = self.provider.telemetry_model.cpu_name
        return self._format_or_dash(name)

    @property
    def cpu_number(self) -> str:
        return self._format_or_dash(self.provider.telemetry_model.cpu_number, "{:.0f}")

    @property
    def cpu_is_virtual(self) -> str:
        val = self.provider.telemetry_model.cpu_is_virtual
        return "yes" if val else "no" if val is not None else "N/A"

    @property
    def ram(self) -> str:
        used = self.provider.telemetry_model.usage_ram
        total = self.provider.telemetry_model.total_ram
        return (
            f"{used:.2f}/{total:.2f} GB"
            if used is not None and total is not None
            else "N/A"
        )

    @property
    def storage(self) -> str:
        used = self.provider.telemetry_model.used_provider_space
        total = self.provider.telemetry_model.total_provider_space
        return (
            f"{used:.2f}/{total:.2f} GB"
            if used is not None and total is not None
            else "N/A"
        )

    @property
    def disk_read_speed(self) -> str:
        return self._format_or_dash(self.provider.telemetry_model.qd64_disk_read_speed)

    @property
    def disk_write_speed(self) -> str:
        return self._format_or_dash(self.provider.telemetry_model.qd64_disk_write_speed)

    @property
    def speed_download(self) -> str:
        val = self.provider.telemetry_model.speedtest_download
        return self._format_or_dash(val / 1024**2, "{:.2f} Mbps")

    @property
    def speed_upload(self) -> str:
        val = self.provider.telemetry_model.speedtest_upload
        return self._format_or_dash(val / 1024**2, "{:.2f} Mbps")

    @property
    def ping(self) -> str:
        return self._format_or_dash(
            self.provider.telemetry_model.speedtest_ping, "{:.2f} ms"
        )

    @property
    def country(self) -> str:
        return self._format_or_dash(self.provider.telemetry_model.country)

    @property
    def isp(self) -> str:
        return self._format_or_dash(self.provider.telemetry_model.isp)

    @property
    def working_time(self) -> str:
        return self.provider.working_time or str(0)

    @property
    def reg_time(self) -> str:
        return self.provider.reg_time or str(0)

    @property
    def min_span(self) -> str:
        return self.provider.min_span or str(0)

    @property
    def max_span(self) -> str:
        return self.provider.max_span or str(0)

    @property
    def storage_git_hash(self) -> str:
        return self._format_or_dash(self.provider.telemetry_model.storage_git_hash)

    @property
    def provider_git_hash(self) -> str:
        return self._format_or_dash(self.provider.telemetry_model.provider_git_hash)

    @property
    def status_emoji(self) -> str:
        status = self.provider.status
        if status is None:
            return "⚪️"  # No Data
        if status == 0:
            r = self._get_ratio()
            return "🔴" if r < 0.8 else ("🟡" if r < 0.99 else "🟢")
        if status == 2:
            return "🟠"  # Invalid
        if status == 3:
            return "🔴"  # Not Store
        if status == 500:
            return "⚫️"  # Not Accessible
        return "⚪️"  # Unknown

    @property
    def status_text(self) -> str:
        status = self.provider.status
        if status is None:
            return "No Data"
        if status == 0:
            r = self._get_ratio()
            if r < 0.8:
                label = "Unstable"
            elif r < 0.99:
                label = "Partial"
            else:
                label = "Stable"
            r_percent = "(100%)" if r == 1.0 else f"({r * 100:.1f}%)"
            return f"{label} {r_percent}"
        if status == 2:
            return "Invalid"
        if status == 3:
            return "Not Store"
        if status == 500:
            return "Not Accessible"
        return "Unknown"
