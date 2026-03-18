"""Add unique constraint to users_subscriptions

Revision ID: d9ec12d69856
Revises: 22dc6859ebe3
Create Date: 2026-03-18 17:00:50.020519

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9ec12d69856'
down_revision: Union[str, Sequence[str], None] = '22dc6859ebe3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        DELETE FROM users_subscriptions
        WHERE rowid NOT IN (
            SELECT MIN(rowid)
            FROM users_subscriptions
            GROUP BY user_id, provider_pubkey
        );
        """
    )
    with op.batch_alter_table('users_subscriptions') as batch_op:
        batch_op.create_unique_constraint('uq_user_provider_subscription', ['user_id', 'provider_pubkey'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users_subscriptions') as batch_op:
        batch_op.drop_constraint('uq_user_provider_subscription', type_='unique')
