from apiq import AsyncClientAPI, async_endpoint, AsyncAPINamespace
from apiq.types import HTTPMethod

from .models import (
    ProvidersResponse,
    ProviderSearchPayload,
    TelemetryResponse,
)
from ...config import MYTONPROVIDER_API_KEY


class Providers(AsyncAPINamespace):
    namespace = "providers"

    @async_endpoint(HTTPMethod.POST, path="/search", return_as=ProvidersResponse)
    async def search(self, payload: ProviderSearchPayload) -> ProvidersResponse:
        pass


class MyTONProviderAPI(AsyncClientAPI):
    headers = {"Authorization": MYTONPROVIDER_API_KEY}
    base_url = "https://mytonprovider.org/api/"
    version = "v1"

    @property
    def providers(self) -> Providers:
        return Providers(self)

    @async_endpoint(HTTPMethod.GET, path="/providers", return_as=TelemetryResponse)
    async def telemetry(self) -> TelemetryResponse:
        pass
