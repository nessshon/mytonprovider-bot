from apiq import AsyncClientAPI, async_endpoint
from apiq.types import HTTPMethod

from .models import AccountStatesResponse
from ...config import TONCENTER_API_KEY


class TONCenterAPI(AsyncClientAPI):
    headers = {"X-API-Key": TONCENTER_API_KEY}
    base_url = "https://toncenter.com/api"
    version = "v3"

    max_retries = 5
    rps = 5

    @async_endpoint(
        HTTPMethod.GET,
        path="/accountStates",
        return_as=AccountStatesResponse,
    )
    async def account_state(self, address: str) -> AccountStatesResponse:
        pass
