"""
0007_phase6_addendum.py — Phase 6 Addendum: Report Security, Audit Trail & Worker Reliability

Adds nullable columns to generated_reports for:
  - file_uuid: UUID used as actual filename on disk (never raw user input)
  - retry_count: how many times generation was retried
  - job_priority: lower value = higher priority (default 5)
  - last_downloaded_at: UTC timestamp of last download
  - download_count: total number of downloads
  - audit_log_json: JSON array of audit events (created/started/completed/failed/downloaded/regenerated)
  - template_version: report template version string
  - data_schema_version: data schema version string
  - source_record_refs: JSON array of {table, id} source record references
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("generated_reports") as batch_op:
        batch_op.add_column(sa.Column("file_uuid", sa.String(36), nullable=True, unique=False))
        batch_op.add_column(sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("job_priority", sa.Integer, nullable=False, server_default="5"))
        batch_op.add_column(sa.Column("last_downloaded_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("download_count", sa.Integer, nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("audit_log_json", sa.Text, nullable=True))
        batch_op.add_column(sa.Column("template_version", sa.String(20), nullable=False, server_default="1.0"))
        batch_op.add_column(sa.Column("data_schema_version", sa.String(20), nullable=False, server_default="1.0"))
        batch_op.add_column(sa.Column("source_record_refs", sa.Text, nullable=True))

    op.create_index(
        "ix_generated_reports_job_priority",
        "generated_reports",
        ["job_priority", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_generated_reports_job_priority", table_name="generated_reports")
    with op.batch_alter_table("generated_reports") as batch_op:
        batch_op.drop_column("source_record_refs")
        batch_op.drop_column("data_schema_version")
        batch_op.drop_column("template_version")
        batch_op.drop_column("audit_log_json")
        batch_op.drop_column("download_count")
        batch_op.drop_column("last_downloaded_at")
        batch_op.drop_column("job_priority")
        batch_op.drop_column("retry_count")
        batch_op.drop_column("file_uuid")

