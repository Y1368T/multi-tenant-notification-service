"""Add callbackUrl and callbackHeaders columns to outbox tables

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-02-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add callbackUrl and callbackHeaders to smsOutbox
    op.add_column('smsOutbox', sa.Column('callbackUrl', sa.String(), nullable=True))
    op.add_column('smsOutbox', sa.Column('callbackHeaders', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Add callbackUrl and callbackHeaders to emailOutbox
    op.add_column('emailOutbox', sa.Column('callbackUrl', sa.String(), nullable=True))
    op.add_column('emailOutbox', sa.Column('callbackHeaders', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Add callbackUrl and callbackHeaders to inAppOutbox
    op.add_column('inAppOutbox', sa.Column('callbackUrl', sa.String(), nullable=True))
    op.add_column('inAppOutbox', sa.Column('callbackHeaders', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    # Remove from inAppOutbox
    op.drop_column('inAppOutbox', 'callbackHeaders')
    op.drop_column('inAppOutbox', 'callbackUrl')
    
    # Remove from emailOutbox
    op.drop_column('emailOutbox', 'callbackHeaders')
    op.drop_column('emailOutbox', 'callbackUrl')
    
    # Remove from smsOutbox
    op.drop_column('smsOutbox', 'callbackHeaders')
    op.drop_column('smsOutbox', 'callbackUrl')


