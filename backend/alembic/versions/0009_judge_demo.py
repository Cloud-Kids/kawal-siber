"""Judge demo database initialization with synthetic data.

Revision ID: 0009_judge_demo
Revises: 0008_report_audit_events
Create Date: 2026-11-15 07:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import json

# revision identifiers, used by Alembic.
revision = '0009_judge_demo'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create judge demo database with synthetic data."""
    # This migration is specifically for the judge demo database
    # It creates synthetic data for demonstration purposes
    
    # Get the database connection
    bind = op.get_bind()
    session = Session(bind=bind)
    
    try:
        # Import models
        from app.models import (
            Asset, ScanScope, Incident, WebTarget, WebAssessment,
            WebFinding, AITriageRun, GeneratedReport, SecurityEvent,
            PcapAnalysis
        )
        
        # Create synthetic scan scope
        scope = ScanScope(
            name="Judge Demo Lab Scope",
            cidr="192.168.100.0/24",
            description="Isolated synthetic lab for public judge demonstration",
            authorization_reference="JUDGE-DEMO-2026",
            enabled=True,
            expires_at=datetime(2027, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        )
        session.add(scope)
        session.flush()
        
        # Create synthetic assets
        assets = [
            Asset(
                name="Synthetic Web Server",
                target_ip="synthetic-target",
                port=8080,
                status="SAFE",
                availability_status="UP",
                scope_id=scope.id
            ),
            Asset(
                name="Synthetic API Server",
                target_ip="synthetic-target",
                port=8081,
                status="WARNING",
                availability_status="UP",
                scope_id=scope.id
            ),
            Asset(
                name="Synthetic Database",
                target_ip="synthetic-target",
                port=5432,
                status="SAFE",
                availability_status="UP",
                scope_id=scope.id
            )
        ]
        session.add_all(assets)
        session.flush()
        
        # Create synthetic web target
        web_target = WebTarget(
            name="Synthetic Demo Target",
            target_url="http://synthetic-target:8080",
            hostname="synthetic-target",
            protocol="http",
            port=8080,
            allowed_paths="/*",
            scope_id=scope.id,
            enabled=True,
            authorization_reference="JUDGE-DEMO-2026"
        )
        session.add(web_target)
        session.flush()
        
        # Create synthetic incidents
        incidents = [
            Incident(
                asset_id=assets[0].id,
                timestamp=datetime.now(timezone.utc),
                source_ip="192.168.100.10",
                attack_type="SQL_INJECTION",
                payload="SELECT * FROM users WHERE id=1 OR 1=1",
                severity="HIGH",
                ai_analysis="Potential SQL injection attempt detected in web assessment",
                is_mitigated=False
            ),
            Incident(
                asset_id=assets[1].id,
                timestamp=datetime.now(timezone.utc),
                source_ip="192.168.100.20",
                attack_type="XSS",
                payload="<script>alert('XSS')</script>",
                severity="MEDIUM",
                ai_analysis="Cross-site scripting attempt detected",
                is_mitigated=True
            ),
            Incident(
                asset_id=assets[2].id,
                timestamp=datetime.now(timezone.utc),
                source_ip="192.168.100.30",
                attack_type="BRUTE_FORCE",
                payload="Multiple failed login attempts",
                severity="LOW",
                ai_analysis="Brute force attack pattern detected",
                is_mitigated=False
            )
        ]
        session.add_all(incidents)
        session.flush()
        
        # Create synthetic web assessment
        assessment = WebAssessment(
            web_target_id=web_target.id,
            assessment_profile="PASSIVE",
            status="COMPLETED",
            tool_name="Deep Eye",
            tool_version="1.4.0",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            duration_ms=1500,
            total_findings=3,
            critical_count=0,
            high_count=1,
            medium_count=1,
            low_count=1,
            output_reference="Synthetic assessment completed"
        )
        session.add(assessment)
        session.flush()
        
        # Create synthetic web findings
        findings = [
            WebFinding(
                assessment_id=assessment.id,
                web_target_id=web_target.id,
                title="Missing Content-Security-Policy Header",
                vulnerability_type="MISSING_SECURITY_HEADER",
                severity="HIGH",
                confidence="HIGH",
                finding_status="CONFIRMED",
                affected_url="http://synthetic-target:8080/",
                description="The application does not set a Content-Security-Policy header",
                evidence="HTTP/1.1 200 OK\nContent-Type: text/html",
                remediation="Add Content-Security-Policy header to prevent XSS attacks",
                reference="https://owasp.org/www-project-secure-headers/",
                fingerprint="demo-finding-001",
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc)
            ),
            WebFinding(
                assessment_id=assessment.id,
                web_target_id=web_target.id,
                title="Missing X-Frame-Options Header",
                vulnerability_type="MISSING_SECURITY_HEADER",
                severity="MEDIUM",
                confidence="HIGH",
                finding_status="CONFIRMED",
                affected_url="http://synthetic-target:8080/",
                description="The application does not set X-Frame-Options header",
                evidence="HTTP/1.1 200 OK\nContent-Type: text/html",
                remediation="Add X-Frame-Options header to prevent clickjacking",
                reference="https://owasp.org/www-community/attacks/Clickjacking",
                fingerprint="demo-finding-002",
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc)
            ),
            WebFinding(
                assessment_id=assessment.id,
                web_target_id=web_target.id,
                title="Server Version Disclosure",
                vulnerability_type="INFORMATION_DISCLOSURE",
                severity="LOW",
                confidence="MEDIUM",
                finding_status="NEEDS_REVIEW",
                affected_url="http://synthetic-target:8080/",
                description="Server version information is disclosed in headers",
                evidence="Server: nginx/1.27.0",
                remediation="Remove or obfuscate server version information",
                reference="https://owasp.org/www-community/attacks/Information_disclosure",
                fingerprint="demo-finding-003",
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc)
            )
        ]
        session.add_all(findings)
        session.flush()
        
        # Create synthetic security events
        events = [
            SecurityEvent(
                event_id="judge-demo-event-001",
                event_type="HTTP_REQUEST",
                asset_id=assets[0].id,
                timestamp=datetime.now(timezone.utc),
                source_ip="192.168.100.10",
                destination_ip="synthetic-target",
                destination_port=8080,
                protocol="HTTP",
                severity=2,
                category="WEB",
                signature_id=1001,
                signature="DEMO HTTP GET /api/users",
                confidence="HIGH",
                raw_event=json.dumps({"description": "HTTP GET request to /api/users", "payload": "GET /api/users HTTP/1.1"}),
                pcap_analysis_id=None
            ),
            SecurityEvent(
                event_id="judge-demo-event-002",
                event_type="SUSPICIOUS_ACTIVITY",
                asset_id=assets[1].id,
                timestamp=datetime.now(timezone.utc),
                source_ip="192.168.100.20",
                destination_ip="synthetic-target",
                destination_port=8081,
                protocol="HTTP",
                severity=3,
                category="WEB",
                signature_id=1002,
                signature="DEMO SQL injection attempt",
                confidence="HIGH",
                raw_event=json.dumps({"description": "Suspicious SQL injection attempt", "payload": "SELECT * FROM users WHERE id=1 OR 1=1"}),
                pcap_analysis_id=None
            )
        ]
        session.add_all(events)
        session.flush()
        
        # Create synthetic AI triage run
        triage_run = AITriageRun(
            incident_id=incidents[0].id,
            status="COMPLETED",
            provider="rule_based",
            model_name="heuristic-v1",
            prompt_version="v1",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            confidence_score=0.85,
            input_fingerprint="judge-demo-triage-001",
            result_json=json.dumps({
                "threat_category": "SQL_INJECTION",
                "priority_score": 8,
                "recommended_actions": [
                    "Review input validation",
                    "Implement parameterized queries",
                    "Add WAF rules"
                ],
                "analysis_summary": "High-confidence SQL injection attempt detected"
            })
        )
        session.add(triage_run)
        session.flush()
        
        # Create synthetic report
        report = GeneratedReport(
            report_id="JUDGE-DEMO-REPORT-001",
            report_type="EXECUTIVE",
            format="PDF",
            title="Judge Demo Security Report",
            generation_status="COMPLETED",
            generated_by="Judge Demo System",
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            file_path="/data/reports/judge-demo-report-001.pdf",
            file_size=102400,
            sha256_checksum="demo-hash-001",
            parameters_json=json.dumps({
                "demo": True,
                "environment": "judge",
                "synthetic": True
            })
        )
        session.add(report)
        session.flush()
        
        # Commit all changes
        session.commit()
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def downgrade() -> None:
    """Remove judge demo data."""
    # This would remove all synthetic data
    # For safety, we don't implement downgrade for judge demo
    pass
