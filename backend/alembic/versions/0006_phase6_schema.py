"""
0006_phase6_schema.py — Phase 6: Automated Security Reporting Engine

Adds:
  - generated_reports table
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "generated_reports",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("report_id", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("report_type", sa.String(50), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("format", sa.String(10), nullable=False),
        sa.Column("file_path", sa.String(512), nullable=True),
        sa.Column("file_size", sa.Integer, nullable=True),
        sa.Column("sha256_checksum", sa.String(64), nullable=True),
        sa.Column(
            "generation_status",
            sa.String(20),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("generated_by", sa.String(100), nullable=False, server_default="Operator"),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("parameters_json", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "generation_status IN ('PENDING','RUNNING','COMPLETED','FAILED')",
            name="ck_generated_reports_status_valid",
        ),
        sa.CheckConstraint(
            "report_type IN ('EXECUTIVE','TECHNICAL','ASSESSMENT','OPERATIONS','AI_INTELLIGENCE')",
            name="ck_generated_reports_type_valid",
        ),
        sa.CheckConstraint(
            "format IN ('PDF','HTML','JSON','CSV')",
            name="ck_generated_reports_format_valid",
        ),
    )
    op.create_index(
        "ix_generated_reports_generation_status",
        "generated_reports",
        ["generation_status"],
    )
    op.create_index(
        "ix_generated_reports_created_at",
        "generated_reports",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_table("generated_reports")

