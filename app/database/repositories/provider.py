from ._base import BaseRepository
from ..models import (
    ProviderModel,
    TelemetryModel,
    TelemetryHistoryModel,
)


class ProviderRepository(BaseRepository[ProviderModel]):
    model = ProviderModel


class TelemetryRepository(BaseRepository[TelemetryModel]):
    model = TelemetryModel


class TelemetryHistoryRepository(BaseRepository[TelemetryHistoryModel]):
    model = TelemetryHistoryModel
