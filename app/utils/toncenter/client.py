import typing as t

from apiq import AsyncClientAPI, async_endpoint
from apiq.types import HTTPMethod

from .models import TransactionList
from ...config import TONCENTER_API_KEY


class TONCenterAPI(AsyncClientAPI):
    headers = {"X-API-Key": TONCENTER_API_KEY}
    base_url = "https://toncenter.com/api"
    version = "v3"

    max_retries = 5
    rps = 9

    @async_endpoint(
        HTTPMethod.GET,
        path="/transactions",
        return_as=TransactionList,
    )
    async def transactions(
        self,
        account: t.Union[str, list[str]],
        limit: int = 100,
        sort: str = "desc",
        start_utime: t.Optional[int] = None,
        end_utime: t.Optional[int] = None,
        lt: t.Optional[int] = None,
        start_lt: t.Optional[int] = None,
        end_lt: t.Optional[int] = None,
        offset: t.Optional[int] = None,
    ) -> TransactionList:
        pass
