"""Add WhatsApp tables (templates, notifications, outbox, tenant configurations)

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-07-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6g7h8i9'
down_revision: Union[str, None] = 'c3d4e5f6g7h8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### WhatsApp templates ###
    op.create_table(
        'whatsAppTemplates',
        sa.Column('tenantId', sa.UUID(), nullable=False),
        sa.Column('templateName', sa.String(), nullable=False),
        sa.Column('content', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('isActive', sa.Boolean(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('serviceName', sa.String(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('createdAt', sa.DateTime(), nullable=True),
        sa.Column('updatedAt', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenantId'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenantId', 'serviceName', 'templateName', 'version', name='uix_tenant_whatsApp_template')
    )
    op.create_index(op.f('ix_whatsAppTemplates_id'), 'whatsAppTemplates', ['id'], unique=False)

    # ### WhatsApp notifications ###
    op.create_table(
        'whatsAppNotifications',
        sa.Column('recipientNumber', sa.String(), nullable=False),
        sa.Column('messageContent', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('isRead', sa.Boolean(), nullable=False),
        sa.Column('externalId', sa.String(), nullable=True),
        sa.Column('idempotencyKey', sa.String(), nullable=False),
        sa.Column('templateId', sa.UUID(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('createdAt', sa.DateTime(), nullable=True),
        sa.Column('updatedAt', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['templateId'], ['whatsAppTemplates.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('templateId', 'recipientNumber', 'idempotencyKey', name='uix_whatsApp_notification'),
        sa.UniqueConstraint('idempotencyKey')
    )
    op.create_index(op.f('ix_whatsAppNotifications_id'), 'whatsAppNotifications', ['id'], unique=False)
    op.create_index('ix_whatsApp_notifications_external_id', 'whatsAppNotifications', ['externalId'], unique=False)

    # ### WhatsApp outbox ###
    op.create_table(
        'whatsAppOutbox',
        sa.Column('templateId', sa.UUID(), nullable=True),
        sa.Column('recipientNumber', sa.String(), nullable=False),
        sa.Column('messageContent', sa.String(), nullable=False),
        sa.Column('idempotencyKey', sa.String(), nullable=False),
        sa.Column('retryCount', sa.Integer(), nullable=True),
        sa.Column('lastRetryAt', sa.DateTime(), nullable=True),
        sa.Column('lastErrorMessage', sa.String(), nullable=True),
        sa.Column('nextRetryAt', sa.DateTime(), nullable=True),
        sa.Column('providerAttempted', sa.String(), nullable=True),
        sa.Column('isSent', sa.Boolean(), nullable=True),
        sa.Column('sentAt', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('callbackUrl', sa.String(), nullable=True),
        sa.Column('callbackHeaders', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('createdAt', sa.DateTime(), nullable=True),
        sa.Column('updatedAt', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['templateId'], ['whatsAppTemplates.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('templateId', 'recipientNumber', 'idempotencyKey', name='uix_whatsApp_outbox'),
        sa.UniqueConstraint('idempotencyKey')
    )
    op.create_index(op.f('ix_whatsAppOutbox_id'), 'whatsAppOutbox', ['id'], unique=False)

    # ### Tenant WhatsApp configurations ###
    op.create_table(
        'tenantWhatsAppConfigurations',
        sa.Column('tenantId', sa.UUID(), nullable=False),
        sa.Column('providerName', sa.String(), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('isActive', sa.Boolean(), nullable=True),
        sa.Column('rateLimitPerMinute', sa.Integer(), nullable=True),
        sa.Column('rateLimitPerHour', sa.Integer(), nullable=True),
        sa.Column('rateLimitPerDay', sa.Integer(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('createdAt', sa.DateTime(), nullable=True),
        sa.Column('updatedAt', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenantId'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('tenantId', 'id'),
        sa.UniqueConstraint('tenantId', 'providerName', name='uix_tenant_whatsapp_provider')
    )
    op.create_index(op.f('ix_tenantWhatsAppConfigurations_id'), 'tenantWhatsAppConfigurations', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_tenantWhatsAppConfigurations_id'), table_name='tenantWhatsAppConfigurations')
    op.drop_table('tenantWhatsAppConfigurations')

    op.drop_index(op.f('ix_whatsAppOutbox_id'), table_name='whatsAppOutbox')
    op.drop_table('whatsAppOutbox')

    op.drop_index('ix_whatsApp_notifications_external_id', table_name='whatsAppNotifications')
    op.drop_index(op.f('ix_whatsAppNotifications_id'), table_name='whatsAppNotifications')
    op.drop_table('whatsAppNotifications')

    op.drop_index(op.f('ix_whatsAppTemplates_id'), table_name='whatsAppTemplates')
    op.drop_table('whatsAppTemplates')
