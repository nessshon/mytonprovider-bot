import typing as t

from pydantic import BaseModel


class AccountStateFull(BaseModel):
    address: str
    balance: str
    status: str


class AccountStatesResponse(BaseModel):
    accounts: list[AccountStateFull]


class ActionDetails(BaseModel):
    opcode: t.Optional[str]
    source: t.Optional[str]
    destination: t.Optional[str]
    value: t.Optional[str]
    extra_currencies: t.Optional[t.Dict[str, t.Any]] = None


class Message(BaseModel):
    hash: str
    source: t.Optional[str]
    destination: t.Optional[str]
    value: t.Optional[int]
    fwd_fee: t.Optional[int]
    ihr_fee: t.Optional[int]
    created_lt: t.Optional[int]
    created_at: t.Optional[int]
    opcode: t.Optional[str]
    ihr_disabled: t.Optional[bool]
    bounce: t.Optional[bool]
    bounced: t.Optional[bool]
    import_fee: t.Optional[int]


class AccountState(BaseModel):
    hash: str
    balance: t.Optional[int] = 0
    account_status: t.Optional[str] = None
    frozen_hash: t.Optional[str] = None
    code_hash: t.Optional[str] = None
    data_hash: t.Optional[str] = None


class Transaction(BaseModel):
    account: str
    hash: str
    lt: int
    now: int
    orig_status: str
    end_status: str
    total_fees: int
    prev_trans_hash: str
    prev_trans_lt: int
    description: t.Any
    in_msg: Message
    out_msgs: t.List[Message]
    account_state_before: t.Optional[AccountState]
    account_state_after: t.Optional[AccountState]
    mc_block_seqno: t.Optional[int]


class TransactionList(BaseModel):
    transactions: t.List[Transaction] = []
