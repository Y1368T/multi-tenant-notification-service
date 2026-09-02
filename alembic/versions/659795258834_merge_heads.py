"""merge heads

Revision ID: 659795258834
Revises: 0eb4c093e82a, 93cd74a22120
Create Date: 2026-09-01 14:07:58.472565

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '659795258834'
down_revision: Union[str, Sequence[str], None] = ('0eb4c093e82a', '93cd74a22120')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
