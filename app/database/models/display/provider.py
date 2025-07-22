import typing as t

if t.TYPE_CHECKING:
    from ...models import ProviderModel


class ProviderDisplay:

    def __init__(self, provider: "ProviderModel") -> None:
        self.provider = provider

    @property
    def short_pubkey(self) -> str:
        return f"{self.provider.pubkey[:8]}...{self.provider.pubkey[-8:]}"

    @property
    def uptime(self) -> str:
        return f"{self.provider.uptime:.2f}%"

    @property
    def price(self) -> str:
        return f"{self.provider.price / 1e9:.2f} TON"

    @property
    def max_bag_size(self) -> str:
        return f"{self.provider.max_bag_size_bytes / 1073741824:.2f}"

    @property
    def rating(self) -> str:
        return f"{self.provider.rating:.2f}"

    @property
    def status_emoji(self) -> str:
        ratio = self.provider.uptime / 100 if self.provider.uptime else 0
        status = self.provider.status
        if status is None:
            return "⚪️"
        if status == 0:
            if ratio < 0.8:
                return "🔴"
            elif ratio < 0.99:
                return "🟡"
            return "🟢"
        if status == 2:
            return "🟠"
        if status == 3:
            return "🚫"
        if status == 500:
            return "⚫️"
        return "⚪️"

    @property
    def status_text(self) -> str:
        ratio = self.provider.uptime / 100 if self.provider.uptime else 0
        status = self.provider.status
        if status is None:
            return "No Data"
        if status == 0:
            if ratio < 0.8:
                return "Unstable"
            elif ratio < 0.99:
                return "Partial"
            return "Stable"
        if status == 2:
            return "Invalid"
        if status == 3:
            return "Not Store"
        if status == 500:
            return "Not Accessible"
        return "Unknown"
