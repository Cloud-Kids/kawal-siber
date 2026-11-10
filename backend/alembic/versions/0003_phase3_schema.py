"""
Phase 3 schema: security_events, pcap_analyses for Suricata IDS integration.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-07 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- pcap_analyses ---
    op.create_table(
        "pcap_analyses",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False, index=True),
        sa.Column("file_size_bytes", sa.Integer, nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("event_count", sa.Integer, nullable=True),
        sa.Column("alert_count", sa.Integer, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')",
            name="ck_pcap_analyses_status_valid",
        ),
    )
    op.create_index("ix_pcap_analyses_status", "pcap_analyses", ["status"])
    op.create_index("ix_pcap_analyses_created_at", "pcap_analyses", ["created_at"])

    # --- security_events ---
    op.create_table(
        "security_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.String(128), nullable=False, unique=True, index=True),
        sa.Column(
            "pcap_analysis_id",
            sa.Integer,
            sa.ForeignKey("pcap_analyses.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "asset_id",
            sa.Integer,
            sa.ForeignKey("assets.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("event_type", sa.String(30), nullable=False, index=True),
        sa.Column("source_ip", sa.String(45), nullable=True, index=True),
        sa.Column("destination_ip", sa.String(45), nullable=True, index=True),
        sa.Column("source_port", sa.Integer, nullable=True),
        sa.Column("destination_port", sa.Integer, nullable=True),
        sa.Column("protocol", sa.String(20), nullable=True),
        sa.Column("signature_id", sa.Integer, nullable=True, index=True),
        sa.Column("signature", sa.String(512), nullable=True),
        sa.Column("category", sa.String(128), nullable=True),
        sa.Column("severity", sa.Integer, nullable=True, index=True),
        sa.Column("confidence", sa.String(20), nullable=True),
        sa.Column("raw_event", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_security_events_timestamp_type",
        "security_events",
        ["timestamp", "event_type"],
    )


def downgrade() -> None:
    op.drop_table("security_events")
    op.drop_table("pcap_analyses")

