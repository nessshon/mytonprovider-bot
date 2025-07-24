from pydantic import BaseModel


class AccountStateFull(BaseModel):
    address: str
    balance: str
    status: str


class AccountStatesResponse(BaseModel):
    accounts: list[AccountStateFull]
