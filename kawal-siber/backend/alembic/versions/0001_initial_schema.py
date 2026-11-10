"""Initial schema: assets and incidents tables.

Revision ID: 0001
Revises: None
Create Date: 2024-01-01 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------
    # Table: assets
    # -----------------------------------------------------------------
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("target_ip", sa.String(length=253), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="UNKNOWN"),
        sa.Column("response_time_ms", sa.Float(), nullable=True),
        sa.Column("last_scanned", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("port >= 1 AND port <= 65535", name="ck_assets_port_range"),
        sa.CheckConstraint(
            "status IN ('UNKNOWN', 'SAFE', 'WARNING', 'UNDER_ATTACK', 'DOWN')",
            name="ck_assets_status_valid",
        ),
        sa.CheckConstraint(
            "response_time_ms IS NULL OR response_time_ms >= 0",
            name="ck_assets_response_time_non_negative",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assets_name"), "assets", ["name"], unique=False)
    op.create_index(op.f("ix_assets_target_ip"), "assets", ["target_ip"], unique=False)
    op.create_index(op.f("ix_assets_status"), "assets", ["status"], unique=False)

    # -----------------------------------------------------------------
    # Table: incidents
    # -----------------------------------------------------------------
    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_ip", sa.String(length=45), nullable=False),
        sa.Column("attack_type", sa.String(length=30), nullable=False),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(length=10), nullable=False),
        sa.Column("ai_analysis", sa.Text(), nullable=True),
        sa.Column("is_mitigated", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.CheckConstraint(
            "attack_type IN ('BRUTE_FORCE', 'SQL_INJECTION', 'XSS', 'PORT_SCAN', 'ANOMALY_TRAFFIC')",
            name="ck_incidents_attack_type_valid",
        ),
        sa.CheckConstraint(
            "severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'PENDING')",
            name="ck_incidents_severity_valid",
        ),
        sa.CheckConstraint(
            "payload IS NULL OR length(payload) <= 65536",
            name="ck_incidents_payload_length",
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
            name="fk_incidents_asset_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_incidents_asset_id"), "incidents", ["asset_id"], unique=False)
    op.create_index(op.f("ix_incidents_timestamp"), "incidents", ["timestamp"], unique=False)
    op.create_index(op.f("ix_incidents_severity"), "incidents", ["severity"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_incidents_severity"), table_name="incidents")
    op.drop_index(op.f("ix_incidents_timestamp"), table_name="incidents")
    op.drop_index(op.f("ix_incidents_asset_id"), table_name="incidents")
    op.drop_table("incidents")

    op.drop_index(op.f("ix_assets_status"), table_name="assets")
    op.drop_index(op.f("ix_assets_target_ip"), table_name="assets")
    op.drop_index(op.f("ix_assets_name"), table_name="assets")
    op.drop_table("assets")
