"""add message aggregates hourly

Revision ID: g2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-07-28 07:38:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'g2b3c4d5e6f7'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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
    
    # Create a unique constraint to ensure we don't have duplicate rows for the same bucket/tenant/channel/provider/status
    op.create_index('ix_msg_agg_unique_bucket', 'message_aggregates_hourly', ['timeBucket', 'tenantId', 'channel', 'provider', 'status'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_msg_agg_unique_bucket', table_name='message_aggregates_hourly')
    op.drop_index(op.f('ix_message_aggregates_hourly_status'), table_name='message_aggregates_hourly')
    op.drop_index(op.f('ix_message_aggregates_hourly_provider'), table_name='message_aggregates_hourly')
    op.drop_index(op.f('ix_message_aggregates_hourly_channel'), table_name='message_aggregates_hourly')
    op.drop_index(op.f('ix_message_aggregates_hourly_tenantId'), table_name='message_aggregates_hourly')
    op.drop_index(op.f('ix_message_aggregates_hourly_timeBucket'), table_name='message_aggregates_hourly')
    op.drop_index(op.f('ix_message_aggregates_hourly_id'), table_name='message_aggregates_hourly')
    op.drop_table('message_aggregates_hourly')
