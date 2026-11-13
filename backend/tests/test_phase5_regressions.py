"""Phase 5 regression tests: Deep Eye authz context + UTC timestamp guard."""
from __future__ import annotations

import pytest

from app.integrations.deep_eye.adapter import deep_eye_adapter


# ---------- Deep Eye authorization context ----------

def test_adapter_accepts_extra_allowed_hosts(monkeypatch):
    """Public IP passes validation ONLY when explicitly authorized.
    Network engine is stubbed — no external requests."""
    monkeypatch.setattr(
        deep_eye_adapter, "_run_deterministic_passive", lambda **kw: []
    )
    r = deep_eye_adapter.execute_assessment(
        target_url="http://34.209.65.97:80/",
        profile="PASSIVE",
        allowed_paths="/*",
        extra_allowed_hosts={"34.209.65.97"},
    )
    assert r.success is True


def test_adapter_rejects_unauthorized_public_ip():
    r = deep_eye_adapter.execute_assessment(
        target_url="http://34.209.65.97:80/",
        profile="PASSIVE",
        allowed_paths="/*",
    )
    assert r.success is False
    assert "scope" in (r.error_message or "").lower()


def test_adapter_localhost_still_allowed(monkeypatch):
    monkeypatch.setattr(
        deep_eye_adapter, "_run_deterministic_passive", lambda **kw: []
    )
    r = deep_eye_adapter.execute_assessment(
        target_url="http://127.0.0.1:9/",
        profile="PASSIVE",
        allowed_paths="/*",
    )
    assert "scope" not in (r.error_message or "").lower()


def test_adapter_wrong_asset_host_rejected():
    """Authorizing a DIFFERENT IP must not allow this target."""
    r = deep_eye_adapter.execute_assessment(
        target_url="http://34.209.65.97:80/",
        profile="PASSIVE",
        allowed_paths="/*",
        extra_allowed_hosts={"10.0.0.99"},
    )
    assert r.success is False
    assert "scope" in (r.error_message or "").lower()


# ---------- UTC timestamp serialization ----------

def test_naive_datetime_gets_z_suffix():
    from fastapi.testclient import TestClient
    from app.main import app
    import json, re

    client = TestClient(app)
    # health endpoint returns a timestamp? use any JSON endpoint with datetime.
    # Instead test the regex directly on a synthetic payload.
    from app.main import _NAIVE_DT_RE
    sample = '{"created_at":"2026-11-13T09:22:00","other":"2026-11-13T09:22:00+00:00","d":"2026-11-13 09:22:00"}'
    fixed = _NAIVE_DT_RE.sub(r"\1Z", sample)
    assert '"2026-11-13T09:22:00Z"' in fixed
    assert '"2026-11-13 09:22:00Z"' in fixed
    assert '"2026-11-13T09:22:00+00:00"' in fixed  # aware untouched
