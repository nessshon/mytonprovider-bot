"""add thresholds_data to users.alert_settings

Revision ID: f56468262429
Revises: 330c9695b258
Create Date: 2025-08-10 10:57:24.857124

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f56468262429"
down_revision: Union[str, Sequence[str], None] = "330c9695b258"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
DEFAULT_JSON = {
    "cpu_high": 90,
    "ram_high": 90,
    "network_high": 90,
    "disk_load_high": 90,
    "disk_space_low": 90,
}
TABLE = "users.alert_settings"
COL = "thresholds_data"


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c["name"] for c in insp.get_columns(table)]
    return column in cols


def upgrade():
    if not _has_column(TABLE, COL):
        op.add_column(
            TABLE,
            sa.Column(COL, sa.JSON(), nullable=True),
        )

    stmt = sa.text(f'UPDATE "{TABLE}" SET {COL} = :val WHERE {COL} IS NULL')
    stmt = stmt.bindparams(sa.bindparam("val", value=DEFAULT_JSON, type_=sa.JSON()))
    op.execute(stmt)

    with op.batch_alter_table(TABLE, recreate="always") as b:
        b.alter_column(COL, existing_type=sa.JSON(), nullable=False)


def downgrade():
    with op.batch_alter_table(TABLE, recreate="always") as b:
        b.drop_column(COL)
