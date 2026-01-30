"""add_tenant_callback_columns

Revision ID: a1b2c3d4e5f6
Revises: 55df0bb094ef
Create Date: 2026-01-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '55df0bb094ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add callback URL and headers columns to tenants table for fire-and-forget mode."""
    # Add callbackUrl column - webhook URL for notification status updates
    op.add_column(
        'tenants',
        sa.Column(
            'callbackUrl',
            sa.String(),
            nullable=True,
            comment='Webhook URL for notification status callbacks (fire-and-forget mode)'
        )
    )
    
    # Add callbackHeaders column - optional auth headers for callback
    op.add_column(
        'tenants',
        sa.Column(
            'callbackHeaders',
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment='Optional HTTP headers for callback authentication'
        )
    )


def downgrade() -> None:
    """Remove callback columns from tenants table."""
    op.drop_column('tenants', 'callbackHeaders')
    op.drop_column('tenants', 'callbackUrl')

