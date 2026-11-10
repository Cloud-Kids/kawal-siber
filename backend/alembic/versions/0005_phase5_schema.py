"""
0005_phase5_schema.py — Phase 5: AI Triage & Incident Correlation Engine

Adds:
  - ai_triage_runs table
  - incident_evidence table
  - incident_timeline_events table
  - lifecycle_status column to incidents
  - acknowledged_at, investigated_at, resolved_at, resolution_notes to incidents
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # 1. Extend incidents table with lifecycle columns
    # -----------------------------------------------------------------------
    with op.batch_alter_table("incidents") as batch_op:
        batch_op.add_column(
            sa.Column(
                "lifecycle_status",
                sa.String(20),
                nullable=False,
                server_default="OPEN",
            )
        )
        batch_op.add_column(
            sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("investigated_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("resolution_notes", sa.Text, nullable=True)
        )

    op.create_index(
        "ix_incidents_lifecycle_status",
        "incidents",
        ["lifecycle_status"],
    )

    # -----------------------------------------------------------------------
    # 2. ai_triage_runs table
    # -----------------------------------------------------------------------
    op.create_table(
        "ai_triage_runs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "incident_id",
            sa.Integer,
            sa.ForeignKey("incidents.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=True),
        sa.Column("prompt_version", sa.String(20), nullable=False, server_default="v1"),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("input_fingerprint", sa.String(64), nullable=True),
        sa.Column("result_json", sa.Text, nullable=True),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('PENDING','RUNNING','COMPLETED','FAILED','REQUIRES_REVIEW')",
            name="ck_ai_triage_runs_status_valid",
        ),
    )
    op.create_index(
        "ix_ai_triage_runs_input_fingerprint",
        "ai_triage_runs",
        ["input_fingerprint"],
    )
    op.create_index(
        "ix_ai_triage_runs_created_at",
        "ai_triage_runs",
        ["created_at"],
    )

    # -----------------------------------------------------------------------
    # 3. incident_evidence table
    # -----------------------------------------------------------------------
    op.create_table(
        "incident_evidence",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "incident_id",
            sa.Integer,
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("source_record_id", sa.Integer, nullable=True),
        sa.Column("relationship_type", sa.String(50), nullable=True),
        sa.Column("evidence_summary", sa.Text, nullable=True),
        sa.Column("evidence_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_type IN ('SURICATA_EVENT','WEB_FINDING','NMAP_RESULT','MANUAL_EVIDENCE')",
            name="ck_incident_evidence_source_type_valid",
        ),
        sa.UniqueConstraint(
            "incident_id",
            "source_type",
            "source_record_id",
            name="uq_incident_evidence_incident_source",
        ),
    )

    # -----------------------------------------------------------------------
    # 4. incident_timeline_events table
    # -----------------------------------------------------------------------
    op.create_table(
        "incident_timeline_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "incident_id",
            sa.Integer,
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("source_type", sa.String(30), nullable=True),
        sa.Column("source_record_id", sa.Integer, nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_incident_timeline_events_timestamp",
        "incident_timeline_events",
        ["timestamp"],
    )


def downgrade() -> None:
    op.drop_table("incident_timeline_events")
    op.drop_table("incident_evidence")
    op.drop_table("ai_triage_runs")

    op.drop_index("ix_incidents_lifecycle_status", table_name="incidents")
    with op.batch_alter_table("incidents") as batch_op:
        batch_op.drop_column("resolution_notes")
        batch_op.drop_column("resolved_at")
        batch_op.drop_column("investigated_at")
        batch_op.drop_column("acknowledged_at")
        batch_op.drop_column("lifecycle_status")

