import typing as t

from .base import BaseModel


class ContractBagsRequest(BaseModel):
    provider: t.Optional[str] = None
    limit: int = 500
    offset: int = 0


class ContractInfo(BaseModel):
    address: str
    provider_pubkey: str
    bag_id: str
    owner_address: str
    size: int
    reason: t.Optional[int] = None
    reason_timestamp: t.Optional[int] = None


class ContractBagsResponse(BaseModel):
    contracts: t.List[ContractInfo]
    total: int
