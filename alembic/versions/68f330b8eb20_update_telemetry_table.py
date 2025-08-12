"""update telemetry table

Revision ID: 68f330b8eb20
Revises: b258d73bc69d
Create Date: 2025-08-12 13:37:53.058279
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "68f330b8eb20"
down_revision: Union[str, Sequence[str], None] = "b258d73bc69d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns(table)}
    return column in cols


def upgrade() -> None:
    """Upgrade schema (idempotent)."""

    if not _has_column("telemetry", "bytes_recv"):
        op.add_column(
            "telemetry", sa.Column("bytes_recv", sa.BigInteger(), nullable=True)
        )
    if not _has_column("telemetry", "bytes_sent"):
        op.add_column(
            "telemetry", sa.Column("bytes_sent", sa.BigInteger(), nullable=True)
        )
    if not _has_column("telemetry", "net_recv"):
        op.add_column("telemetry", sa.Column("net_recv", sa.JSON(), nullable=True))
    if not _has_column("telemetry", "net_sent"):
        op.add_column("telemetry", sa.Column("net_sent", sa.JSON(), nullable=True))
    if not _has_column("telemetry", "timestamp"):
        op.add_column("telemetry", sa.Column("timestamp", sa.Integer(), nullable=True))

    with op.batch_alter_table("telemetry") as batch_op:
        if _has_column("telemetry", "x_real_ip"):
            batch_op.drop_column("x_real_ip")
        if _has_column("telemetry", "benchmark"):
            batch_op.drop_column("benchmark")


def downgrade() -> None:
    """Downgrade schema (idempotent)."""

    with op.batch_alter_table("telemetry") as batch_op:
        if not _has_column("telemetry", "x_real_ip"):
            batch_op.add_column(sa.Column("x_real_ip", sa.String(), nullable=False))
        if not _has_column("telemetry", "benchmark"):
            batch_op.add_column(sa.Column("benchmark", sa.JSON(), nullable=True))

    for col in ("timestamp", "net_sent", "net_recv", "bytes_sent", "bytes_recv"):
        if _has_column("telemetry", col):
            op.drop_column("telemetry", col)
