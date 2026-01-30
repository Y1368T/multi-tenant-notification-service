"""Add externalId and isRead columns to notification tables

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns to inAppNotifications table
    op.add_column('inAppNotifications', sa.Column('isRead', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('inAppNotifications', sa.Column('externalId', sa.String(), nullable=True))
    op.create_index('ix_inapp_notifications_external_id', 'inAppNotifications', ['externalId'], unique=False)

    # Add columns to emailNotifications table
    op.add_column('emailNotifications', sa.Column('isRead', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('emailNotifications', sa.Column('externalId', sa.String(), nullable=True))
    op.create_index('ix_email_notifications_external_id', 'emailNotifications', ['externalId'], unique=False)

    # Add columns to smsNotifications table
    op.add_column('smsNotifications', sa.Column('isRead', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('smsNotifications', sa.Column('externalId', sa.String(), nullable=True))
    op.create_index('ix_sms_notifications_external_id', 'smsNotifications', ['externalId'], unique=False)


def downgrade() -> None:
    # Remove columns from smsNotifications table
    op.drop_index('ix_sms_notifications_external_id', table_name='smsNotifications')
    op.drop_column('smsNotifications', 'externalId')
    op.drop_column('smsNotifications', 'isRead')

    # Remove columns from emailNotifications table
    op.drop_index('ix_email_notifications_external_id', table_name='emailNotifications')
    op.drop_column('emailNotifications', 'externalId')
    op.drop_column('emailNotifications', 'isRead')

    # Remove columns from inAppNotifications table
    op.drop_index('ix_inapp_notifications_external_id', table_name='inAppNotifications')
    op.drop_column('inAppNotifications', 'externalId')
    op.drop_column('inAppNotifications', 'isRead')


