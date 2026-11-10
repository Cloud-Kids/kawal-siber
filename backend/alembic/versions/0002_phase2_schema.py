"""Phase 2 schema: scan_scopes, scan_jobs, scan_results, and asset availability/scope.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-05 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------
    # Table: scan_scopes
    # -----------------------------------------------------------------
    op.create_table(
        "scan_scopes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("cidr", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("authorization_reference", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("length(cidr) > 0", name="ck_scan_scopes_cidr_non_empty"),
        sa.CheckConstraint(
            "length(authorization_reference) > 0",
            name="ck_scan_scopes_auth_ref_non_empty",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scan_scopes_name"), "scan_scopes", ["name"], unique=False)
    op.create_index(op.f("ix_scan_scopes_cidr"), "scan_scopes", ["cidr"], unique=False)
    op.create_index(op.f("ix_scan_scopes_enabled"), "scan_scopes", ["enabled"], unique=False)
    op.create_index(op.f("ix_scan_scopes_expires_at"), "scan_scopes", ["expires_at"], unique=False)

    # -----------------------------------------------------------------
    # Alter Table: assets (availability_status & scope_id)
    # Using batch_alter_table for SQLite compatibility
    # -----------------------------------------------------------------
    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "availability_status",
                sa.String(length=10),
                nullable=False,
                server_default="UNKNOWN",
            )
        )
        batch_op.add_column(
            sa.Column("scope_id", sa.Integer(), nullable=True)
        )
        batch_op.create_check_constraint(
            "ck_assets_availability_status_valid",
            "availability_status IN ('UNKNOWN', 'UP', 'DOWN')",
        )
        batch_op.create_foreign_key(
            "fk_assets_scope_id",
            "scan_scopes",
            ["scope_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            op.f("ix_assets_availability_status"),
            ["availability_status"],
            unique=False,
        )
        batch_op.create_index(
            op.f("ix_assets_scope_id"),
            ["scope_id"],
            unique=False,
        )

    # -----------------------------------------------------------------
    # Table: scan_jobs
    # -----------------------------------------------------------------
    op.create_table(
        "scan_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("resolved_ip", sa.String(length=50), nullable=True),
        sa.Column("scanner_version", sa.String(length=100), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')",
            name="ck_scan_jobs_status_valid",
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
            name="fk_scan_jobs_asset_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scan_jobs_asset_id"), "scan_jobs", ["asset_id"], unique=False)
    op.create_index(op.f("ix_scan_jobs_status"), "scan_jobs", ["status"], unique=False)
    op.create_index(op.f("ix_scan_jobs_created_at"), "scan_jobs", ["created_at"], unique=False)

    # -----------------------------------------------------------------
    # Table: scan_results
    # -----------------------------------------------------------------
    op.create_table(
        "scan_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scan_job_id", sa.Integer(), nullable=False),
        sa.Column("protocol", sa.String(length=10), nullable=False, server_default="tcp"),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("service_name", sa.String(length=100), nullable=True),
        sa.Column("product", sa.String(length=150), nullable=True),
        sa.Column("version", sa.String(length=100), nullable=True),
        sa.Column("extra_info", sa.String(length=255), nullable=True),
        sa.Column("reason", sa.String(length=100), nullable=True),
        sa.CheckConstraint("port >= 1 AND port <= 65535", name="ck_scan_results_port_range"),
        sa.ForeignKeyConstraint(
            ["scan_job_id"],
            ["scan_jobs.id"],
            name="fk_scan_results_scan_job_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scan_results_scan_job_id"), "scan_results", ["scan_job_id"], unique=False)


def downgrade() -> None:
    # Drop scan_results
    op.drop_index(op.f("ix_scan_results_scan_job_id"), table_name="scan_results")
    op.drop_table("scan_results")

    # Drop scan_jobs
    op.drop_index(op.f("ix_scan_jobs_created_at"), table_name="scan_jobs")
    op.drop_index(op.f("ix_scan_jobs_status"), table_name="scan_jobs")
    op.drop_index(op.f("ix_scan_jobs_asset_id"), table_name="scan_jobs")
    op.drop_table("scan_jobs")

    # Drop added columns from assets
    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.drop_index(op.f("ix_assets_scope_id"))
        batch_op.drop_index(op.f("ix_assets_availability_status"))
        batch_op.drop_constraint("fk_assets_scope_id", type_="foreignkey")
        batch_op.drop_constraint("ck_assets_availability_status_valid", type_="check")
        batch_op.drop_column("scope_id")
        batch_op.drop_column("availability_status")

    # Drop scan_scopes
    op.drop_index(op.f("ix_scan_scopes_expires_at"), table_name="scan_scopes")
    op.drop_index(op.f("ix_scan_scopes_enabled"), table_name="scan_scopes")
    op.drop_index(op.f("ix_scan_scopes_cidr"), table_name="scan_scopes")
    op.drop_index(op.f("ix_scan_scopes_name"), table_name="scan_scopes")
    op.drop_table("scan_scopes")

