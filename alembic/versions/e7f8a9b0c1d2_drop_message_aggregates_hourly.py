"""drop message_aggregates_hourly

Revision ID: e7f8a9b0c1d2
Revises: 659795258834
Create Date: 2026-09-04 02:22:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e7f8a9b0c1d2'
down_revision: Union[str, Sequence[str], None] = '659795258834'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop legacy message_aggregates_hourly table and its indexes."""
    op.execute("DROP TABLE IF EXISTS message_aggregates_hourly CASCADE")


def downgrade() -> None:
    """Recreate message_aggregates_hourly table."""
    op.create_table(
        'message_aggregates_hourly',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('createdAt', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updatedAt', sa.DateTime(timezone=True), nullable=True),
        sa.Column('timeBucket', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tenantId', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('channel', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('messageCount', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_message_aggregates_hourly_id'), 'message_aggregates_hourly', ['id'], unique=False)
    op.create_index(op.f('ix_message_aggregates_hourly_timeBucket'), 'message_aggregates_hourly', ['timeBucket'], unique=False)
    op.create_index(op.f('ix_message_aggregates_hourly_tenantId'), 'message_aggregates_hourly', ['tenantId'], unique=False)
    op.create_index(op.f('ix_message_aggregates_hourly_channel'), 'message_aggregates_hourly', ['channel'], unique=False)
    op.create_index(op.f('ix_message_aggregates_hourly_provider'), 'message_aggregates_hourly', ['provider'], unique=False)
    op.create_index(op.f('ix_message_aggregates_hourly_status'), 'message_aggregates_hourly', ['status'], unique=False)
    op.create_index('ix_msg_agg_unique_bucket', 'message_aggregates_hourly', ['timeBucket', 'tenantId', 'channel', 'provider', 'status'], unique=True)
