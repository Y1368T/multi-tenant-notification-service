"""convert_all_to_camelcase

Revision ID: cb16b753108
Revises: ff4db9a60419
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'cb16b753108'
down_revision: Union[str, Sequence[str], None] = '4e9ed9d8ab73'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert all table and column names from snake_case to camelCase."""
    
    # Rename tables
    op.rename_table('sms_templates', 'smsTemplates')
    op.rename_table('sms_notifications', 'smsNotifications')
    op.rename_table('sms_outbox', 'smsOutbox')
    op.rename_table('in_app_templates', 'inAppTemplates')
    op.rename_table('in_app_notifications', 'inAppNotifications')
    op.rename_table('in_app_outbox', 'inAppOutbox')
    op.rename_table('email_templates', 'emailTemplates')
    op.rename_table('email_notifications', 'emailNotifications')
    op.rename_table('email_outbox', 'emailOutbox')
    op.rename_table('tenant_sms_configurations', 'tenantSmsConfigurations')
    op.rename_table('tenant_inapp_configurations', 'tenantInappConfigurations')
    op.rename_table('tenant_email_configurations', 'tenantEmailConfigurations')
    
    # Rename columns in tenants table
    op.alter_column('tenants', 'is_active', new_column_name='isActive')
    op.alter_column('tenants', 'api_keys', new_column_name='apiKeys')
    op.alter_column('tenants', 'supported_channels', new_column_name='supportedChannels')
    op.alter_column('tenants', 'prefered_communication_method', new_column_name='preferedCommunicationMethod')
    op.alter_column('tenants', 'rate_limit_per_minute', new_column_name='rateLimitPerMinute')
    op.alter_column('tenants', 'rate_limit_per_hour', new_column_name='rateLimitPerHour')
    op.alter_column('tenants', 'rate_limit_per_day', new_column_name='rateLimitPerDay')
    op.alter_column('tenants', 'created_at', new_column_name='createdAt')
    op.alter_column('tenants', 'updated_at', new_column_name='updatedAt')
    
    # Rename columns in smsTemplates table
    op.alter_column('smsTemplates', 'tenant_id', new_column_name='tenantId')
    op.alter_column('smsTemplates', 'template_name', new_column_name='templateName')
    op.alter_column('smsTemplates', 'is_active', new_column_name='isActive')
    op.alter_column('smsTemplates', 'service_name', new_column_name='serviceName')
    op.alter_column('smsTemplates', 'created_at', new_column_name='createdAt')
    op.alter_column('smsTemplates', 'updated_at', new_column_name='updatedAt')
    
    # Rename columns in smsNotifications table
    op.alter_column('smsNotifications', 'recipient_number', new_column_name='recipientNumber')
    op.alter_column('smsNotifications', 'message_content', new_column_name='messageContent')
    op.alter_column('smsNotifications', 'idempotency_key', new_column_name='idempotencyKey')
    op.alter_column('smsNotifications', 'template_id', new_column_name='templateId')
    op.alter_column('smsNotifications', 'created_at', new_column_name='createdAt')
    op.alter_column('smsNotifications', 'updated_at', new_column_name='updatedAt')
    
    # Rename columns in smsOutbox table
    op.alter_column('smsOutbox', 'template_id', new_column_name='templateId')
    op.alter_column('smsOutbox', 'recipient_number', new_column_name='recipientNumber')
    op.alter_column('smsOutbox', 'message_content', new_column_name='messageContent')
    op.alter_column('smsOutbox', 'idempotency_key', new_column_name='idempotencyKey')
    op.alter_column('smsOutbox', 'retry_count', new_column_name='retryCount')
    op.alter_column('smsOutbox', 'last_retry_at', new_column_name='lastRetryAt')
    op.alter_column('smsOutbox', 'last_error_message', new_column_name='lastErrorMessage')
    op.alter_column('smsOutbox', 'next_retry_at', new_column_name='nextRetryAt')
    op.alter_column('smsOutbox', 'provider_attempted', new_column_name='providerAttempted')
    op.alter_column('smsOutbox', 'is_sent', new_column_name='isSent')
    op.alter_column('smsOutbox', 'sent_at', new_column_name='sentAt')
    op.alter_column('smsOutbox', 'created_at', new_column_name='createdAt')
    op.alter_column('smsOutbox', 'updated_at', new_column_name='updatedAt')
    
    # Rename columns in inAppTemplates table
    op.alter_column('inAppTemplates', 'template_name', new_column_name='templateName')
    op.alter_column('inAppTemplates', 'is_active', new_column_name='isActive')
    op.alter_column('inAppTemplates', 'service_name', new_column_name='serviceName')
    op.alter_column('inAppTemplates', 'tenant_id', new_column_name='tenantId')
    op.alter_column('inAppTemplates', 'created_at', new_column_name='createdAt')
    op.alter_column('inAppTemplates', 'updated_at', new_column_name='updatedAt')
    
    # Rename columns in inAppNotifications table
    op.alter_column('inAppNotifications', 'recipient_user_id', new_column_name='recipientUserId')
    op.alter_column('inAppNotifications', 'message_content', new_column_name='messageContent')
    op.alter_column('inAppNotifications', 'idempotency_key', new_column_name='idempotencyKey')
    op.alter_column('inAppNotifications', 'template_id', new_column_name='templateId')
    op.alter_column('inAppNotifications', 'created_at', new_column_name='createdAt')
    op.alter_column('inAppNotifications', 'updated_at', new_column_name='updatedAt')
    
    # Rename columns in inAppOutbox table
    op.alter_column('inAppOutbox', 'template_id', new_column_name='templateId')
    op.alter_column('inAppOutbox', 'recipient_user_id', new_column_name='recipientUserId')
    op.alter_column('inAppOutbox', 'message_content', new_column_name='messageContent')
    op.alter_column('inAppOutbox', 'idempotency_key', new_column_name='idempotencyKey')
    op.alter_column('inAppOutbox', 'retry_count', new_column_name='retryCount')
    op.alter_column('inAppOutbox', 'last_retry_at', new_column_name='lastRetryAt')
    op.alter_column('inAppOutbox', 'last_error_message', new_column_name='lastErrorMessage')
    op.alter_column('inAppOutbox', 'next_retry_at', new_column_name='nextRetryAt')
    op.alter_column('inAppOutbox', 'provider_attempted', new_column_name='providerAttempted')
    op.alter_column('inAppOutbox', 'is_sent', new_column_name='isSent')
    op.alter_column('inAppOutbox', 'sent_at', new_column_name='sentAt')
    op.alter_column('inAppOutbox', 'created_at', new_column_name='createdAt')
    op.alter_column('inAppOutbox', 'updated_at', new_column_name='updatedAt')
    
    # Rename columns in emailTemplates table
    op.alter_column('emailTemplates', 'template_name', new_column_name='templateName')
    op.alter_column('emailTemplates', 'body_type', new_column_name='bodyType')
    op.alter_column('emailTemplates', 'file_urls', new_column_name='fileUrls')
    op.alter_column('emailTemplates', 'is_active', new_column_name='isActive')
    op.alter_column('emailTemplates', 'service_name', new_column_name='serviceName')
    op.alter_column('emailTemplates', 'tenant_id', new_column_name='tenantId')
    op.alter_column('emailTemplates', 'created_at', new_column_name='createdAt')
    op.alter_column('emailTemplates', 'updated_at', new_column_name='updatedAt')
    
    # Rename columns in emailNotifications table
    op.alter_column('emailNotifications', 'recipient_email', new_column_name='recipientEmail')
    op.alter_column('emailNotifications', 'message_content', new_column_name='messageContent')
    op.alter_column('emailNotifications', 'idempotency_key', new_column_name='idempotencyKey')
    op.alter_column('emailNotifications', 'template_id', new_column_name='templateId')
    op.alter_column('emailNotifications', 'created_at', new_column_name='createdAt')
    op.alter_column('emailNotifications', 'updated_at', new_column_name='updatedAt')
    
    # Rename columns in emailOutbox table
    op.alter_column('emailOutbox', 'template_id', new_column_name='templateId')
    op.alter_column('emailOutbox', 'recipient_email', new_column_name='recipientEmail')
    op.alter_column('emailOutbox', 'message_content', new_column_name='messageContent')
    op.alter_column('emailOutbox', 'idempotency_key', new_column_name='idempotencyKey')
    op.alter_column('emailOutbox', 'retry_count', new_column_name='retryCount')
    op.alter_column('emailOutbox', 'last_retry_at', new_column_name='lastRetryAt')
    op.alter_column('emailOutbox', 'last_error_message', new_column_name='lastErrorMessage')
    op.alter_column('emailOutbox', 'next_retry_at', new_column_name='nextRetryAt')
    op.alter_column('emailOutbox', 'provider_attempted', new_column_name='providerAttempted')
    op.alter_column('emailOutbox', 'is_sent', new_column_name='isSent')
    op.alter_column('emailOutbox', 'sent_at', new_column_name='sentAt')
    op.alter_column('emailOutbox', 'created_at', new_column_name='createdAt')
    op.alter_column('emailOutbox', 'updated_at', new_column_name='updatedAt')
    
    # Rename columns in tenantSmsConfigurations table
    op.alter_column('tenantSmsConfigurations', 'tenant_id', new_column_name='tenantId')
    op.alter_column('tenantSmsConfigurations', 'provider_name', new_column_name='providerName')
    op.alter_column('tenantSmsConfigurations', 'is_active', new_column_name='isActive')
    op.alter_column('tenantSmsConfigurations', 'rate_limit_per_minute', new_column_name='rateLimitPerMinute')
    op.alter_column('tenantSmsConfigurations', 'rate_limit_per_hour', new_column_name='rateLimitPerHour')
    op.alter_column('tenantSmsConfigurations', 'rate_limit_per_day', new_column_name='rateLimitPerDay')
    op.alter_column('tenantSmsConfigurations', 'created_at', new_column_name='createdAt')
    op.alter_column('tenantSmsConfigurations', 'updated_at', new_column_name='updatedAt')
    
    # Rename columns in tenantInappConfigurations table
    op.alter_column('tenantInappConfigurations', 'tenant_id', new_column_name='tenantId')
    op.alter_column('tenantInappConfigurations', 'provider_name', new_column_name='providerName')
    op.alter_column('tenantInappConfigurations', 'is_active', new_column_name='isActive')
    op.alter_column('tenantInappConfigurations', 'rate_limit_per_minute', new_column_name='rateLimitPerMinute')
    op.alter_column('tenantInappConfigurations', 'rate_limit_per_hour', new_column_name='rateLimitPerHour')
    op.alter_column('tenantInappConfigurations', 'rate_limit_per_day', new_column_name='rateLimitPerDay')
    op.alter_column('tenantInappConfigurations', 'created_at', new_column_name='createdAt')
    op.alter_column('tenantInappConfigurations', 'updated_at', new_column_name='updatedAt')
    
    # Rename columns in tenantEmailConfigurations table
    op.alter_column('tenantEmailConfigurations', 'tenant_id', new_column_name='tenantId')
    op.alter_column('tenantEmailConfigurations', 'provider_name', new_column_name='providerName')
    op.alter_column('tenantEmailConfigurations', 'is_active', new_column_name='isActive')
    op.alter_column('tenantEmailConfigurations', 'rate_limit_per_minute', new_column_name='rateLimitPerMinute')
    op.alter_column('tenantEmailConfigurations', 'rate_limit_per_hour', new_column_name='rateLimitPerHour')
    op.alter_column('tenantEmailConfigurations', 'rate_limit_per_day', new_column_name='rateLimitPerDay')
    op.alter_column('tenantEmailConfigurations', 'created_at', new_column_name='createdAt')
    op.alter_column('tenantEmailConfigurations', 'updated_at', new_column_name='updatedAt')
    
    # Rename columns in providers table
    op.alter_column('providers', 'provider_name', new_column_name='providerName')
    op.alter_column('providers', 'display_name', new_column_name='displayName')
    op.alter_column('providers', 'docs_url', new_column_name='docsUrl')
    op.alter_column('providers', 'test_endpoint', new_column_name='testEndpoint')
    op.alter_column('providers', 'config_schema', new_column_name='configSchema')
    op.alter_column('providers', 'ui_schema', new_column_name='uiSchema')
    op.alter_column('providers', 'is_active', new_column_name='isActive')
    op.alter_column('providers', 'created_at', new_column_name='createdAt')
    op.alter_column('providers', 'updated_at', new_column_name='updatedAt')
    
    # Update foreign key constraints (they reference table and column names)
    # Note: PostgreSQL will automatically update FK constraints when columns are renamed
    # But we need to update the constraint names if they reference old names
    
    # Update unique constraint column references
    # These will be handled automatically by PostgreSQL when columns are renamed


def downgrade() -> None:
    """Revert all table and column names from camelCase back to snake_case."""
    
    # Revert column renames in providers table
    op.alter_column('providers', 'createdAt', new_column_name='created_at')
    op.alter_column('providers', 'updatedAt', new_column_name='updated_at')
    op.alter_column('providers', 'isActive', new_column_name='is_active')
    op.alter_column('providers', 'uiSchema', new_column_name='ui_schema')
    op.alter_column('providers', 'configSchema', new_column_name='config_schema')
    op.alter_column('providers', 'testEndpoint', new_column_name='test_endpoint')
    op.alter_column('providers', 'docsUrl', new_column_name='docs_url')
    op.alter_column('providers', 'displayName', new_column_name='display_name')
    op.alter_column('providers', 'providerName', new_column_name='provider_name')
    
    # Revert column renames in tenantEmailConfigurations table
    op.alter_column('tenantEmailConfigurations', 'updatedAt', new_column_name='updated_at')
    op.alter_column('tenantEmailConfigurations', 'createdAt', new_column_name='created_at')
    op.alter_column('tenantEmailConfigurations', 'rateLimitPerDay', new_column_name='rate_limit_per_day')
    op.alter_column('tenantEmailConfigurations', 'rateLimitPerHour', new_column_name='rate_limit_per_hour')
    op.alter_column('tenantEmailConfigurations', 'rateLimitPerMinute', new_column_name='rate_limit_per_minute')
    op.alter_column('tenantEmailConfigurations', 'isActive', new_column_name='is_active')
    op.alter_column('tenantEmailConfigurations', 'providerName', new_column_name='provider_name')
    op.alter_column('tenantEmailConfigurations', 'tenantId', new_column_name='tenant_id')
    
    # Revert column renames in tenantInappConfigurations table
    op.alter_column('tenantInappConfigurations', 'updatedAt', new_column_name='updated_at')
    op.alter_column('tenantInappConfigurations', 'createdAt', new_column_name='created_at')
    op.alter_column('tenantInappConfigurations', 'rateLimitPerDay', new_column_name='rate_limit_per_day')
    op.alter_column('tenantInappConfigurations', 'rateLimitPerHour', new_column_name='rate_limit_per_hour')
    op.alter_column('tenantInappConfigurations', 'rateLimitPerMinute', new_column_name='rate_limit_per_minute')
    op.alter_column('tenantInappConfigurations', 'isActive', new_column_name='is_active')
    op.alter_column('tenantInappConfigurations', 'providerName', new_column_name='provider_name')
    op.alter_column('tenantInappConfigurations', 'tenantId', new_column_name='tenant_id')
    
    # Revert column renames in tenantSmsConfigurations table
    op.alter_column('tenantSmsConfigurations', 'updatedAt', new_column_name='updated_at')
    op.alter_column('tenantSmsConfigurations', 'createdAt', new_column_name='created_at')
    op.alter_column('tenantSmsConfigurations', 'rateLimitPerDay', new_column_name='rate_limit_per_day')
    op.alter_column('tenantSmsConfigurations', 'rateLimitPerHour', new_column_name='rate_limit_per_hour')
    op.alter_column('tenantSmsConfigurations', 'rateLimitPerMinute', new_column_name='rate_limit_per_minute')
    op.alter_column('tenantSmsConfigurations', 'isActive', new_column_name='is_active')
    op.alter_column('tenantSmsConfigurations', 'providerName', new_column_name='provider_name')
    op.alter_column('tenantSmsConfigurations', 'tenantId', new_column_name='tenant_id')
    
    # Revert column renames in emailOutbox table
    op.alter_column('emailOutbox', 'updatedAt', new_column_name='updated_at')
    op.alter_column('emailOutbox', 'createdAt', new_column_name='created_at')
    op.alter_column('emailOutbox', 'sentAt', new_column_name='sent_at')
    op.alter_column('emailOutbox', 'isSent', new_column_name='is_sent')
    op.alter_column('emailOutbox', 'providerAttempted', new_column_name='provider_attempted')
    op.alter_column('emailOutbox', 'nextRetryAt', new_column_name='next_retry_at')
    op.alter_column('emailOutbox', 'lastErrorMessage', new_column_name='last_error_message')
    op.alter_column('emailOutbox', 'lastRetryAt', new_column_name='last_retry_at')
    op.alter_column('emailOutbox', 'retryCount', new_column_name='retry_count')
    op.alter_column('emailOutbox', 'idempotencyKey', new_column_name='idempotency_key')
    op.alter_column('emailOutbox', 'messageContent', new_column_name='message_content')
    op.alter_column('emailOutbox', 'recipientEmail', new_column_name='recipient_email')
    op.alter_column('emailOutbox', 'templateId', new_column_name='template_id')
    
    # Revert column renames in emailNotifications table
    op.alter_column('emailNotifications', 'updatedAt', new_column_name='updated_at')
    op.alter_column('emailNotifications', 'createdAt', new_column_name='created_at')
    op.alter_column('emailNotifications', 'templateId', new_column_name='template_id')
    op.alter_column('emailNotifications', 'idempotencyKey', new_column_name='idempotency_key')
    op.alter_column('emailNotifications', 'messageContent', new_column_name='message_content')
    op.alter_column('emailNotifications', 'recipientEmail', new_column_name='recipient_email')
    
    # Revert column renames in emailTemplates table
    op.alter_column('emailTemplates', 'updatedAt', new_column_name='updated_at')
    op.alter_column('emailTemplates', 'createdAt', new_column_name='created_at')
    op.alter_column('emailTemplates', 'tenantId', new_column_name='tenant_id')
    op.alter_column('emailTemplates', 'serviceName', new_column_name='service_name')
    op.alter_column('emailTemplates', 'isActive', new_column_name='is_active')
    op.alter_column('emailTemplates', 'fileUrls', new_column_name='file_urls')
    op.alter_column('emailTemplates', 'bodyType', new_column_name='body_type')
    op.alter_column('emailTemplates', 'templateName', new_column_name='template_name')
    
    # Revert column renames in inAppOutbox table
    op.alter_column('inAppOutbox', 'updatedAt', new_column_name='updated_at')
    op.alter_column('inAppOutbox', 'createdAt', new_column_name='created_at')
    op.alter_column('inAppOutbox', 'sentAt', new_column_name='sent_at')
    op.alter_column('inAppOutbox', 'isSent', new_column_name='is_sent')
    op.alter_column('inAppOutbox', 'providerAttempted', new_column_name='provider_attempted')
    op.alter_column('inAppOutbox', 'nextRetryAt', new_column_name='next_retry_at')
    op.alter_column('inAppOutbox', 'lastErrorMessage', new_column_name='last_error_message')
    op.alter_column('inAppOutbox', 'lastRetryAt', new_column_name='last_retry_at')
    op.alter_column('inAppOutbox', 'retryCount', new_column_name='retry_count')
    op.alter_column('inAppOutbox', 'idempotencyKey', new_column_name='idempotency_key')
    op.alter_column('inAppOutbox', 'messageContent', new_column_name='message_content')
    op.alter_column('inAppOutbox', 'recipientUserId', new_column_name='recipient_user_id')
    op.alter_column('inAppOutbox', 'templateId', new_column_name='template_id')
    
    # Revert column renames in inAppNotifications table
    op.alter_column('inAppNotifications', 'updatedAt', new_column_name='updated_at')
    op.alter_column('inAppNotifications', 'createdAt', new_column_name='created_at')
    op.alter_column('inAppNotifications', 'templateId', new_column_name='template_id')
    op.alter_column('inAppNotifications', 'idempotencyKey', new_column_name='idempotency_key')
    op.alter_column('inAppNotifications', 'messageContent', new_column_name='message_content')
    op.alter_column('inAppNotifications', 'recipientUserId', new_column_name='recipient_user_id')
    
    # Revert column renames in inAppTemplates table
    op.alter_column('inAppTemplates', 'updatedAt', new_column_name='updated_at')
    op.alter_column('inAppTemplates', 'createdAt', new_column_name='created_at')
    op.alter_column('inAppTemplates', 'tenantId', new_column_name='tenant_id')
    op.alter_column('inAppTemplates', 'serviceName', new_column_name='service_name')
    op.alter_column('inAppTemplates', 'isActive', new_column_name='is_active')
    op.alter_column('inAppTemplates', 'templateName', new_column_name='template_name')
    
    # Revert column renames in smsOutbox table
    op.alter_column('smsOutbox', 'updatedAt', new_column_name='updated_at')
    op.alter_column('smsOutbox', 'createdAt', new_column_name='created_at')
    op.alter_column('smsOutbox', 'sentAt', new_column_name='sent_at')
    op.alter_column('smsOutbox', 'isSent', new_column_name='is_sent')
    op.alter_column('smsOutbox', 'providerAttempted', new_column_name='provider_attempted')
    op.alter_column('smsOutbox', 'nextRetryAt', new_column_name='next_retry_at')
    op.alter_column('smsOutbox', 'lastErrorMessage', new_column_name='last_error_message')
    op.alter_column('smsOutbox', 'lastRetryAt', new_column_name='last_retry_at')
    op.alter_column('smsOutbox', 'retryCount', new_column_name='retry_count')
    op.alter_column('smsOutbox', 'idempotencyKey', new_column_name='idempotency_key')
    op.alter_column('smsOutbox', 'messageContent', new_column_name='message_content')
    op.alter_column('smsOutbox', 'recipientNumber', new_column_name='recipient_number')
    op.alter_column('smsOutbox', 'templateId', new_column_name='template_id')
    
    # Revert column renames in smsNotifications table
    op.alter_column('smsNotifications', 'updatedAt', new_column_name='updated_at')
    op.alter_column('smsNotifications', 'createdAt', new_column_name='created_at')
    op.alter_column('smsNotifications', 'templateId', new_column_name='template_id')
    op.alter_column('smsNotifications', 'idempotencyKey', new_column_name='idempotency_key')
    op.alter_column('smsNotifications', 'messageContent', new_column_name='message_content')
    op.alter_column('smsNotifications', 'recipientNumber', new_column_name='recipient_number')
    
    # Revert column renames in smsTemplates table
    op.alter_column('smsTemplates', 'updatedAt', new_column_name='updated_at')
    op.alter_column('smsTemplates', 'createdAt', new_column_name='created_at')
    op.alter_column('smsTemplates', 'serviceName', new_column_name='service_name')
    op.alter_column('smsTemplates', 'isActive', new_column_name='is_active')
    op.alter_column('smsTemplates', 'templateName', new_column_name='template_name')
    op.alter_column('smsTemplates', 'tenantId', new_column_name='tenant_id')
    
    # Revert column renames in tenants table
    op.alter_column('tenants', 'updatedAt', new_column_name='updated_at')
    op.alter_column('tenants', 'createdAt', new_column_name='created_at')
    op.alter_column('tenants', 'rateLimitPerDay', new_column_name='rate_limit_per_day')
    op.alter_column('tenants', 'rateLimitPerHour', new_column_name='rate_limit_per_hour')
    op.alter_column('tenants', 'rateLimitPerMinute', new_column_name='rate_limit_per_minute')
    op.alter_column('tenants', 'preferedCommunicationMethod', new_column_name='prefered_communication_method')
    op.alter_column('tenants', 'supportedChannels', new_column_name='supported_channels')
    op.alter_column('tenants', 'apiKeys', new_column_name='api_keys')
    op.alter_column('tenants', 'isActive', new_column_name='is_active')
    
    # Revert table renames
    op.rename_table('tenantEmailConfigurations', 'tenant_email_configurations')
    op.rename_table('tenantInappConfigurations', 'tenant_inapp_configurations')
    op.rename_table('tenantSmsConfigurations', 'tenant_sms_configurations')
    op.rename_table('emailOutbox', 'email_outbox')
    op.rename_table('emailNotifications', 'email_notifications')
    op.rename_table('emailTemplates', 'email_templates')
    op.rename_table('inAppOutbox', 'in_app_outbox')
    op.rename_table('inAppNotifications', 'in_app_notifications')
    op.rename_table('inAppTemplates', 'in_app_templates')
    op.rename_table('smsOutbox', 'sms_outbox')
    op.rename_table('smsNotifications', 'sms_notifications')
    op.rename_table('smsTemplates', 'sms_templates')

