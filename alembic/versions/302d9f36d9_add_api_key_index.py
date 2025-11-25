"""add_api_key_index

Revision ID: 302d9f36d9
Revises: e6fdd993a475
Create Date: 2025-01-15 12:00:00.000000

"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '302d9f36d9'
down_revision: Union[str, Sequence[str], None] = 'cb16b753108'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add index on tenants.apiKeys column for faster API key lookups."""
    # Create index on apiKeys column for faster tenant lookups by API key
    # Using GIN index would be better for full-text search, but since we're doing exact/prefix matching,
    # a standard B-tree index is sufficient
    op.create_index(
        'ix_tenants_api_keys',
        'tenants',
        ['apiKeys'],
        unique=False,
        postgresql_where=sa.text('"apiKeys" IS NOT NULL')  # Only index non-null values
    )


def downgrade() -> None:
    """Remove index on tenants.apiKeys column."""
    op.drop_index('ix_tenants_api_keys', table_name='tenants')

