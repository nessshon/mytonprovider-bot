import typing as t
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, PrimaryKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from ._base import BaseModel
from ..helpers import now


REASON_DESCRIPTIONS = {
    0: "OK",
    101: "IP not found or unavailable",
    102: "IP not found or unavailable",
    103: "Connection timed out",
    201: "Offline or ports closed",
    202: "Storage contract issues",
    301: "No headers information",
    302: "No headers information",
    401: "Can't proof files availability",
    402: "Can't proof files availability",
    403: "Can't proof files availability",
}


class ContractModel(BaseModel):
    __tablename__ = "contracts"

    address: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_pubkey: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("providers.pubkey", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bag_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    owner_address: Mapped[str] = mapped_column(String(64), nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason: Mapped[t.Optional[int]] = mapped_column(Integer, nullable=True)
    reason_timestamp: Mapped[t.Optional[int]] = mapped_column(BigInteger, nullable=True)

    missing_since: Mapped[t.Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now,
        onupdate=now,
        nullable=True,
    )

    __table_args__ = (
        PrimaryKeyConstraint("address", "provider_pubkey"),
    )
