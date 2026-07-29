"""add_outbox_performance_indexes

Revision ID: 9f8e7d6c5b4a
Revises: d4e5f6g7h8i9
Create Date: 2026-07-16 00:00:00.000000

Every dashboard/analytics endpoint filters by createdAt >= :since and
several also filter/group by status. Right now nothing indexes either
column on the outbox tables (only a uniqueness constraint on
templateId+recipient+idempotencyKey exists). At current data volumes a
full scan is invisible; the moment these tables reach production scale
this is the difference between an instant dashboard and one that times
out. Shipping this before any dashboard endpoint code exists, since it
has zero behavioral risk (it doesn't change what any query returns,
only how fast) and every query written from here on is written and
tested against the shape it'll actually run against.
"""
from typing import Sequence, Union

from alembic import op


revision: str = '9f8e7d6c5b4a'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6g7h8i9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OUTBOX_TABLES = ["smsOutbox", "emailOutbox", "inAppOutbox", "whatsAppOutbox"]


def upgrade() -> None:
    for table in OUTBOX_TABLES:
        op.create_index(
            f"ix_{table}_createdAt_status",
            table,
            ["createdAt", "status"],
        )


def downgrade() -> None:
    for table in OUTBOX_TABLES:
        op.drop_index(f"ix_{table}_createdAt_status", table_name=table)
