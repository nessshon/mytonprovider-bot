from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ._base import BaseModel
from ..helpers import now, now_rounded_hour


class BaseWalletModel(BaseModel):
    __abstract__ = True

    provider_pubkey: Mapped[str] = mapped_column(
        ForeignKey("providers.pubkey"),
        primary_key=True,
    )
    address: Mapped[str] = mapped_column(String(64), nullable=False)
    last_lt: Mapped[int] = mapped_column(BigInteger, nullable=True)
    balance: Mapped[int] = mapped_column(BigInteger, nullable=False)
    earned: Mapped[int] = mapped_column(BigInteger, nullable=False)


class WalletModel(BaseWalletModel):
    __tablename__ = "wallets"

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=now,
        onupdate=now,
    )


class WalletHistoryModel(BaseWalletModel):
    __tablename__ = "wallets_history"

    archived_at: Mapped[datetime] = mapped_column(
        DateTime,
        primary_key=True,
        nullable=False,
        default=now_rounded_hour,
    )
