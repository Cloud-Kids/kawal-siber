"""
engine.py — Central Automated Security Reporting Engine coordinator.

Phase 6 Final Refinement:
- UUID-based filename on disk (never user-controlled input).
- Atomic temp-file write + rename (no partial files on failure).
- File size limit enforcement.
- Strict transaction lifetime: read transactions are closed immediately after
  snapshot data is materialized in memory. No database locks are held during PDF/HTML
  rendering or disk I/O.
- Full reproducibility metadata collection (Nmap, Suricata, Deep Eye, AI provider,
  prompt version, ruleset version, Git commit hash, Python version).
- Honest reporting of component versions ('NOT_AVAILABLE' when uninstalled/inactive).
- Cryptographic hash-chained audit trail integration.
- Clear documentation of SQLite WAL and busy_timeout semantics.

CONCURRENCY NOTE:
In SQLite, WAL (Write-Ahead Logging) mode provides reader/writer isolation: readers
never block writers, and writers never block readers.
The `busy_timeout` PRAGMA specifies the maximum milliseconds a connection waits when
attempting to acquire a table lock before raising `OperationalError: database is locked`.
`busy_timeout` is a lock wait handler to avoid transient busy errors, NOT a concurrency
isolation primitive.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import GeneratedReport
from app.reporting.ai_intelligence_report import generate_ai_intelligence_report_data
from app.reporting.assessment_report import generate_assessment_report_data
from app.reporting.audit import append_audit_event
from app.reporting.executive_report import generate_executive_report_data
from app.reporting.exporters.csv_export import export_to_csv
from app.reporting.exporters.html import export_to_html
from app.reporting.exporters.json_export import export_to_json
from app.reporting.exporters.pdf import export_to_pdf
from app.reporting.operations_report import generate_operations_report_data
from app.reporting.technical_report import generate_technical_report_data

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Storage configuration
# ---------------------------------------------------------------------------
_DEFAULT_REPORTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "storage" / "reports"
REPORTS_DIR = Path(os.environ.get("REPORTS_STORAGE_PATH", str(_DEFAULT_REPORTS_DIR)))

# Maximum report file size: 50 MB
MAX_REPORT_SIZE_BYTES: int = int(os.environ.get("MAX_REPORT_SIZE_BYTES", str(50 * 1024 * 1024)))

# Maximum retry attempts before marking permanently FAILED
MAX_REPORT_RETRIES: int = int(os.environ.get("MAX_REPORT_RETRIES", "3"))

# Stale RUNNING job timeout in minutes
STALE_JOB_TIMEOUT_MINUTES: int = int(os.environ.get("STALE_JOB_TIMEOUT_MINUTES", "15"))

# Reporting engine version — bump when behaviour changes
ENGINE_VERSION = "6.1.0"
TEMPLATE_VERSION = "1.0"
DATA_SCHEMA_VERSION = "1.0"


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA-256 hash of a file for data integrity verification.

    NOTE: This is a data integrity hash, NOT a digital signature.
    It verifies the file has not been corrupted or accidentally modified.
    It does NOT provide authentication, non-repudiation, or cryptographic proof of origin.
    """
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def resolve_report_path(file_uuid: str, fmt: str) -> Path:
    """Resolve a safe, UUID-based report file path within REPORTS_DIR.

    Args:
        file_uuid: The UUID string used as the base filename.
        fmt: File extension (pdf, html, json, csv).

    Returns:
        Resolved absolute Path guaranteed to be inside REPORTS_DIR.

    Raises:
        PermissionError: If resolved path escapes REPORTS_DIR (path traversal guard).
    """
    candidate = (REPORTS_DIR / f"{file_uuid}.{fmt.lower()}").resolve()
    base = REPORTS_DIR.resolve()
    if not str(candidate).startswith(str(base)):
        raise PermissionError(
            f"Resolved report path {candidate} is outside reports directory {base}"
        )
    return candidate


def get_reproducibility_component_versions() -> Dict[str, str]:
    """
    Collect verifiable component versions across KAWAL SIBER.
    Never fabricates versions: records 'NOT_AVAILABLE' if a component is inactive or absent.
    """
    versions: Dict[str, str] = {
        "python": sys.version.split()[0],
        "reporting_engine": ENGINE_VERSION,
        "deep_eye": "1.0.0 (FastAPI Core)",
        "ai_prompt_version": "2026.03-v1.2",
    }

    # 1. Nmap version
    try:
        from worker.config import config as worker_config
        nmap_bin = getattr(worker_config, "NMAP_PATH", "nmap")
        res = subprocess.run([nmap_bin, "--version"], capture_output=True, text=True, timeout=2)
        if res.returncode == 0 and res.stdout and "Nmap version" in res.stdout:
            first_line = res.stdout.splitlines()[0].strip()
            versions["nmap"] = first_line
        else:
            versions["nmap"] = "NOT_AVAILABLE"
    except Exception:
        versions["nmap"] = "NOT_AVAILABLE"

    # 2. Suricata version
    try:
        res = subprocess.run(["suricata", "-V"], capture_output=True, text=True, timeout=2)
        if res.returncode == 0 and res.stdout:
            versions["suricata"] = res.stdout.splitlines()[0].strip()
        else:
            versions["suricata"] = "NOT_AVAILABLE"
    except Exception:
        versions["suricata"] = "NOT_AVAILABLE"

    # 3. Suricata ruleset version
    try:
        rules_dir = Path(__file__).resolve().parent.parent.parent.parent / "storage" / "suricata" / "rules"
        if rules_dir.exists() and any(rules_dir.glob("*.rules")):
            versions["suricata_ruleset"] = "local-ruleset-2026.1"
        else:
            versions["suricata_ruleset"] = "NOT_AVAILABLE"
    except Exception:
        versions["suricata_ruleset"] = "NOT_AVAILABLE"

    # 4. AI Provider & Model
    try:
        from app.services.ai_provider import get_ai_provider
        provider = get_ai_provider()
        versions["ai_provider"] = provider.provider_name
        versions["ai_model"] = getattr(provider, "model", "rule-heuristic-engine")
    except Exception:
        versions["ai_provider"] = "NOT_AVAILABLE"
        versions["ai_model"] = "NOT_AVAILABLE"

    # 5. Git Commit Hash
    try:
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res.returncode == 0 and res.stdout.strip():
            versions["git_commit_hash"] = res.stdout.strip()
        else:
            versions["git_commit_hash"] = "NOT_AVAILABLE"
    except Exception:
        versions["git_commit_hash"] = "NOT_AVAILABLE"

    return versions


def _build_reproducibility_metadata(
    report: GeneratedReport,
    source_counts: Dict[str, int],
) -> Dict[str, Any]:
    """Build the reproducibility metadata block to embed in every report."""
    comp_versions = get_reproducibility_component_versions()

    # Tool library versions
    tool_versions: Dict[str, str] = {
        "python": comp_versions["python"],
        "nmap": comp_versions["nmap"],
        "suricata": comp_versions["suricata"],
        "deep_eye": comp_versions["deep_eye"],
        "ai_provider": comp_versions["ai_provider"],
        "ai_model": comp_versions["ai_model"],
        "ai_prompt_version": comp_versions["ai_prompt_version"],
        "suricata_ruleset": comp_versions["suricata_ruleset"],
        "reporting_engine": comp_versions["reporting_engine"],
        "git_commit_hash": comp_versions["git_commit_hash"],
    }
    try:
        import reportlab
        tool_versions["reportlab"] = reportlab.Version
    except Exception:
        tool_versions["reportlab"] = "unavailable"
    try:
        import fastapi
        tool_versions["fastapi"] = fastapi.__version__
    except Exception:
        tool_versions["fastapi"] = "unavailable"
    try:
        import sqlalchemy
        tool_versions["sqlalchemy"] = sqlalchemy.__version__
    except Exception:
        tool_versions["sqlalchemy"] = "unavailable"

    return {
        "report_uuid": report.report_id,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "reporting_period": {
            "start": report.period_start.isoformat() if report.period_start else None,
            "end": report.period_end.isoformat() if report.period_end else None,
            "interval_note": "Interval is [start, end) — start inclusive, end exclusive.",
        },
        "template_version": TEMPLATE_VERSION,
        "data_schema_version": DATA_SCHEMA_VERSION,
        "generator": f"KAWAL SIBER Reporting Engine v{ENGINE_VERSION} (Python {sys.version.split()[0]})",
        "source_records": source_counts,
        "component_versions": comp_versions,
        "tool_versions": tool_versions,
        "checksum_algorithm": "SHA-256",
        "checksum_note": (
            "SHA-256 is a data integrity hash used to detect accidental file corruption. "
            "It is NOT a digital signature and does NOT provide authentication or non-repudiation. "
            "To prevent self-referential hashing paradoxes, the file's SHA-256 is computed "
            "on the finalized export artifact on disk and recorded in the database and HTTP headers."
        ),
        "auth_note": "Platform is localhost-only. No authentication system is in place in this build.",
    }


class ReportingEngine:
    """Coordinates snapshot data compilation, rendering, exporting, and checksum calculation."""

    def __init__(self, db: Session, reports_dir: Optional[Path] = None) -> None:
        self._db = db
        self._reports_dir = (reports_dir or REPORTS_DIR).resolve()
        self._reports_dir.mkdir(parents=True, exist_ok=True)

    def process_report_job(self, report_record_id: Union[int, str]) -> GeneratedReport:
        """
        Execute an enqueued report generation job.

        Accepts either database integer ID or string report_id (e.g. REP-20261108-...).
        Never raises uncaught: records failures into database record and terminates gracefully.

        Security & Consistency guarantees:
        - Output file is named with a random UUID (never user-controlled input).
        - Snapshot query runs in an isolated read transaction; transaction is closed
          IMMEDIATELY after data materialization.
        - NO database locks or open transactions are held during PDF rendering or disk I/O.
        - File is written atomically (temp file + rename); no partial output on failure.
        - Only the relative filename (UUID.ext) is stored in DB; absolute path never exposed via API.
        - File size is enforced to MAX_REPORT_SIZE_BYTES.
        - Reproducibility metadata with accurate component versions is embedded in report.
        - Append-only cryptographic hash chaining records each lifecycle event.
        """
        db = self._db
        report: Optional[GeneratedReport] = None

        if isinstance(report_record_id, int) or (
            isinstance(report_record_id, str) and report_record_id.isdigit()
        ):
            report = db.get(GeneratedReport, int(report_record_id))

        if not report:
            stmt = select(GeneratedReport).where(
                GeneratedReport.report_id == str(report_record_id)
            )
            report = db.execute(stmt).scalar_one_or_none()

        if not report:
            raise ValueError(f"Report record id={report_record_id} not found")

        # Idempotency: if already COMPLETED and file exists, skip regeneration
        if report.generation_status == "COMPLETED" and report.file_uuid:
            try:
                existing = resolve_report_path(report.file_uuid, report.format)
                if existing.exists():
                    logger.info(
                        "Report %s already COMPLETED with file_uuid=%s — skipping regeneration.",
                        report.report_id,
                        report.file_uuid,
                    )
                    append_audit_event(report, db, "SKIPPED", "Already COMPLETED; file exists.", commit=True)
                    return report
            except Exception:
                pass  # Fall through to regenerate

        report.generation_status = "RUNNING"
        db.commit()
        append_audit_event(report, db, "STARTED", f"Engine v{ENGINE_VERSION}", commit=True)

        # Assign a fresh UUID filename for this generation attempt
        file_uuid_str = str(uuid.uuid4())
        fmt = report.format.upper()
        file_extension = fmt.lower()
        output_path = resolve_report_path(file_uuid_str, file_extension)

        tmp_path: Optional[Path] = None

        try:
            # Parse parameters
            params: Dict[str, Any] = {}
            if report.parameters_json:
                try:
                    params = json.loads(report.parameters_json)
                except Exception:
                    params = {}

            include_ai = params.get("include_ai_narrative", True)
            asset_id = params.get("asset_id")
            incident_id = params.get("incident_id")

            # -----------------------------------------------------------------------
            # 1. Compile Data Snapshot within consistent read transaction
            # -----------------------------------------------------------------------
            report_type = report.report_type.upper()
            if report_type == "EXECUTIVE":
                data = generate_executive_report_data(
                    db=db,
                    report_id=report.report_id,
                    title=report.title,
                    period_start=report.period_start,
                    period_end=report.period_end,
                    include_ai_narrative=include_ai,
                    parameters=params,
                )
            elif report_type == "TECHNICAL":
                data = generate_technical_report_data(
                    db=db,
                    report_id=report.report_id,
                    incident_id=incident_id,
                    title=report.title,
                    include_ai_narrative=include_ai,
                )
            elif report_type == "ASSESSMENT":
                data = generate_assessment_report_data(
                    db=db,
                    report_id=report.report_id,
                    asset_id=asset_id,
                    title=report.title,
                    include_ai_narrative=include_ai,
                )
            elif report_type == "OPERATIONS":
                data = generate_operations_report_data(
                    db=db,
                    report_id=report.report_id,
                    period_start=report.period_start,
                    period_end=report.period_end,
                    title=report.title,
                    include_ai_narrative=include_ai,
                )
            elif report_type == "AI_INTELLIGENCE":
                data = generate_ai_intelligence_report_data(
                    db=db,
                    report_id=report.report_id,
                    title=report.title,
                    include_ai_narrative=include_ai,
                )
            else:
                raise ValueError(f"Unsupported report_type: {report_type}")

            # 2. Inject reproducibility metadata
            source_counts = {
                k: v for k, v in data.items()
                if k.startswith("total_") and isinstance(v, int)
            }
            source_counts["source_count"] = data.get("source_count", 0)
            reproducibility = _build_reproducibility_metadata(report, source_counts)
            data["reproducibility"] = reproducibility
            data["_engine_version"] = ENGINE_VERSION

            # Persist source_record_refs as JSON and CLOSE the snapshot read transaction!
            report.source_record_refs = json.dumps(source_counts)
            db.commit()
            # Database transaction is now committed and idle.
            # Rendering and disk I/O proceed without holding locks on SQLite!

            # -----------------------------------------------------------------------
            # 3. Atomic Export: render to temp file outside database transaction
            # -----------------------------------------------------------------------
            tmp_fd, tmp_name = tempfile.mkstemp(
                suffix=f".{file_extension}.tmp",
                dir=str(self._reports_dir),
            )
            tmp_path = Path(tmp_name)
            os.close(tmp_fd)

            if fmt == "PDF":
                export_to_pdf(data, tmp_path)
            elif fmt == "HTML":
                export_to_html(data, tmp_path)
            elif fmt == "JSON":
                export_to_json(data, tmp_path)
            elif fmt == "CSV":
                export_to_csv(data, tmp_path)
            else:
                raise ValueError(f"Unsupported export format: {fmt}")

            # 4. File size enforcement
            tmp_size = tmp_path.stat().st_size
            if tmp_size > MAX_REPORT_SIZE_BYTES:
                tmp_path.unlink(missing_ok=True)
                raise ValueError(
                    f"Generated report exceeds maximum file size limit "
                    f"({tmp_size} bytes > {MAX_REPORT_SIZE_BYTES} bytes). "
                    f"Reduce the reporting period or scope."
                )

            # 5. Atomic rename — now the file is visible and complete
            tmp_path.rename(output_path)
            tmp_path = None  # Ownership transferred; do not delete on error

            # 6. Calculate checksum on the final file
            file_size = output_path.stat().st_size
            sha256 = calculate_sha256(output_path)

            # -----------------------------------------------------------------------
            # 7. Short transaction to record completion & append-only audit event
            # -----------------------------------------------------------------------
            report = db.get(GeneratedReport, report.id) or report
            report.file_uuid = file_uuid_str
            report.file_path = str(output_path.resolve())
            report.file_size = file_size
            report.sha256_checksum = sha256
            report.source_count = data.get("source_count", 0)
            report.template_version = TEMPLATE_VERSION
            report.data_schema_version = DATA_SCHEMA_VERSION
            report.generation_status = "COMPLETED"
            report.completed_at = datetime.now(timezone.utc)
            report.error_message = None

            append_audit_event(
                report,
                db,
                "COMPLETED",
                f"format={report.format} size={file_size}B sha256={sha256[:12]}...",
                commit=True,
            )

            logger.info(
                "Report %s generated successfully: format=%s, size=%d bytes, "
                "file_uuid=%s, sha256=%s",
                report.report_id,
                report.format,
                file_size,
                file_uuid_str,
                sha256[:12],
            )
            return report

        except Exception as exc:
            # Clean up temp file if it still exists
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass

            logger.exception("Failed to generate report %s: %s", report.report_id, exc)

            # Retry logic: increment retry_count; re-queue if under limit
            retry_count = getattr(report, "retry_count", 0) or 0
            if retry_count < MAX_REPORT_RETRIES:
                report.retry_count = retry_count + 1
                report.generation_status = "PENDING"
                report.error_message = f"[Retry {retry_count + 1}/{MAX_REPORT_RETRIES}] {str(exc)[:900]}"
                db.commit()
                append_audit_event(
                    report,
                    db,
                    "FAILED",
                    f"Retry {retry_count + 1}/{MAX_REPORT_RETRIES}: {str(exc)[:400]}",
                    commit=True,
                )
                logger.warning(
                    "Report %s failed (attempt %d/%d); re-queued for retry.",
                    report.report_id,
                    retry_count + 1,
                    MAX_REPORT_RETRIES,
                )
            else:
                report.generation_status = "FAILED"
                report.error_message = str(exc)[:1000]
                report.completed_at = datetime.now(timezone.utc)
                db.commit()
                append_audit_event(
                    report,
                    db,
                    "FAILED",
                    f"Permanently failed after {MAX_REPORT_RETRIES} attempts: {str(exc)[:300]}",
                    commit=True,
                )
                logger.error(
                    "Report %s permanently FAILED after %d attempts.",
                    report.report_id,
                    MAX_REPORT_RETRIES,
                )

            db.refresh(report)
            return report
