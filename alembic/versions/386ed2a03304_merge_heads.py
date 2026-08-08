"""merge heads

Revision ID: 386ed2a03304
Revises: 16616eadeded, g2b3c4d5e6f7
Create Date: 2026-08-05 14:51:23.615234

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '386ed2a03304'
down_revision: Union[str, Sequence[str], None] = ('16616eadeded', 'g2b3c4d5e6f7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
