"""add_provider_health_columns

Revision ID: f1a2b3c4d5e6
Revises: 9f8e7d6c5b4a
Create Date: 2026-07-16 00:05:00.000000

Required for GET /admin/dashboard/provider-health to return real
lastTestAt/lastTestSuccess instead of null - the contract expects these
populated (see example JSON in GUIDE.md), and ProviderService.testProvider()
previously had nowhere to persist a test result. See the patched
provider_service.py in this same bundle for the write path.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = '9f8e7d6c5b4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('providers', sa.Column('lastTestedAt', sa.DateTime(), nullable=True))
    op.add_column('providers', sa.Column('lastTestSuccess', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('providers', 'lastTestSuccess')
    op.drop_column('providers', 'lastTestedAt')
