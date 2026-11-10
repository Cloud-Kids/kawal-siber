"""
Phase 4 schema: web_targets, web_assessments, web_findings for Web Security & Deep Eye integration.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-07 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- web_targets ---
    op.create_table(
        "web_targets",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "asset_id",
            sa.Integer,
            sa.ForeignKey("assets.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("target_url", sa.String(1024), nullable=False),
        sa.Column("hostname", sa.String(255), nullable=False, index=True),
        sa.Column("protocol", sa.String(10), nullable=False, server_default="http"),
        sa.Column("port", sa.Integer, nullable=False),
        sa.Column("allowed_paths", sa.Text, nullable=True, server_default="/*"),
        sa.Column(
            "scope_id",
            sa.Integer,
            sa.ForeignKey("scan_scopes.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("authorization_reference", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.CheckConstraint("port >= 1 AND port <= 65535", name="ck_web_targets_port_range"),
        sa.CheckConstraint("protocol IN ('http', 'https')", name="ck_web_targets_protocol_valid"),
    )

    # --- web_assessments ---
    op.create_table(
        "web_assessments",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "web_target_id",
            sa.Integer,
            sa.ForeignKey("web_targets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "assessment_profile",
            sa.String(50),
            nullable=False,
            server_default="PASSIVE",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="PENDING",
            index=True,
        ),
        sa.Column(
            "tool_name",
            sa.String(100),
            nullable=False,
            server_default="Deep Eye",
        ),
        sa.Column("tool_version", sa.String(50), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("total_findings", sa.Integer, nullable=False, server_default="0"),
        sa.Column("critical_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("high_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("medium_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("low_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("output_reference", sa.String(512), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
        sa.CheckConstraint(
            "assessment_profile IN ('PASSIVE', 'SAFE_LOCAL')",
            name="ck_web_assessments_profile_valid",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')",
            name="ck_web_assessments_status_valid",
        ),
    )

    # --- web_findings ---
    op.create_table(
        "web_findings",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "assessment_id",
            sa.Integer,
            sa.ForeignKey("web_assessments.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "web_target_id",
            sa.Integer,
            sa.ForeignKey("web_targets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("vulnerability_type", sa.String(100), nullable=False, index=True),
        sa.Column("severity", sa.String(20), nullable=False, index=True),
        sa.Column("confidence", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column(
            "finding_status",
            sa.String(30),
            nullable=False,
            server_default="UNVERIFIED",
            index=True,
        ),
        sa.Column("affected_url", sa.String(1024), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("evidence", sa.Text, nullable=True),
        sa.Column("remediation", sa.Text, nullable=True),
        sa.Column("reference", sa.Text, nullable=True),
        sa.Column(
            "first_seen",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_seen",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("fingerprint", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFORMATIONAL')",
            name="ck_web_findings_severity_valid",
        ),
        sa.CheckConstraint(
            "finding_status IN ('UNVERIFIED', 'NEEDS_REVIEW', 'CONFIRMED', 'FALSE_POSITIVE', 'ACCEPTED_RISK')",
            name="ck_web_findings_status_valid",
        ),
    )


def downgrade() -> None:
    op.drop_table("web_findings")
    op.drop_table("web_assessments")
    op.drop_table("web_targets")

