"""
0008_report_audit_events.py — Phase 6 Final Refinement: Append-Only Audit Trail with Hash Chaining

Adds:
  - report_audit_events table for cryptographic hash-chained audit logging
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_audit_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("report_id", sa.String(64), nullable=False, index=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("actor", sa.String(100), nullable=False, server_default="system"),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("event_details", sa.Text, nullable=True),
        sa.Column("previous_event_hash", sa.String(64), nullable=False, server_default="GENESIS"),
        sa.Column("event_hash", sa.String(64), nullable=False),
    )
    op.create_index(
        "ix_report_audit_events_report_id_id",
        "report_audit_events",
        ["report_id", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_report_audit_events_report_id_id", table_name="report_audit_events")
    op.drop_table("report_audit_events")

