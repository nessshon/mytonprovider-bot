from pyapiq import AsyncClientAPI, AsyncAPINamespace, async_endpoint
from pyapiq.types import HTTPMethod

from .models import (
    ProvidersResponse,
    ProviderSearchPayload,
    TelemetryResponse,
    ContractBagsRequest,
    ContractBagsResponse,
)
from ...config import MYTONPROVIDER_API_KEY


class Providers(AsyncAPINamespace):
    namespace = "providers"

    @async_endpoint(HTTPMethod.POST, path="/search", return_as=ProvidersResponse)
    async def search(self, payload: ProviderSearchPayload) -> ProvidersResponse:
        pass


class Contracts(AsyncAPINamespace):
    namespace = "contracts"

    @async_endpoint(HTTPMethod.POST, path="/bags", return_as=ContractBagsResponse)
    async def bags(self, payload: ContractBagsRequest) -> ContractBagsResponse:
        pass


class MytonproviderClient(AsyncClientAPI):
    headers = {"Authorization": MYTONPROVIDER_API_KEY}
    base_url = "https://mytonprovider.org/api/"
    version = "v1"

    timeout = 30

    rps = 20
    max_retries = 5
    time_period = 1.1

    @property
    def providers(self) -> Providers:
        return Providers(self)

    @property
    def contracts(self) -> Contracts:
        return Contracts(self)

    @async_endpoint(HTTPMethod.GET, path="/providers", return_as=TelemetryResponse)
    async def telemetry(self) -> TelemetryResponse:
        pass
