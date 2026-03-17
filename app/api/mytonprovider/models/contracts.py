import typing as t

from .base import BaseModel


class ContractBagsRequest(BaseModel):
    provider: str


class ContractBagsResponse(BaseModel):
    bags: t.List[str]
