from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from ._base import BaseModel
from ..helpers import now, now_rounded_hour


class BaseWalletModel(BaseModel):
    __abstract__ = True

    address: Mapped[str] = mapped_column(String(64), nullable=False)
    last_lt: Mapped[int] = mapped_column(BigInteger, nullable=True)
    balance: Mapped[int] = mapped_column(BigInteger, nullable=False)
    earned: Mapped[int] = mapped_column(BigInteger, nullable=False)


class WalletModel(BaseWalletModel):
    __tablename__ = "wallets"

    provider_pubkey: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now,
        onupdate=now,
        nullable=True,
    )


class WalletHistoryModel(BaseWalletModel):
    __tablename__ = "wallets_history"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    provider_pubkey: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    archived_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_rounded_hour,
    )

    __table_args__ = (
        Index(
            "idx_wallets_history_pubkey_archived",
            "provider_pubkey",
            "archived_at",
        ),
    )
