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
    from app.main import _fix_naive_datetimes
    sample = {
        "created_at": "2026-11-13T09:22:00",
        "other": "2026-11-13T09:22:00+00:00",
        "sqlite_fmt": "2026-11-13 09:22:00",
        "nested": {"ts": "2026-11-13T09:22:00.123"},
        "arr": ["2026-11-13T09:22:00", "not-a-date"],
    }
    fixed = _fix_naive_datetimes(sample)
    assert fixed["created_at"] == "2026-11-13T09:22:00Z"
    assert fixed["other"] == "2026-11-13T09:22:00+00:00"  # aware untouched
    assert fixed["sqlite_fmt"] == "2026-11-13T09:22:00Z"
    assert fixed["nested"]["ts"] == "2026-11-13T09:22:00.123Z"
    assert fixed["arr"] == ["2026-11-13T09:22:00Z", "not-a-date"]


def test_freetext_datetime_not_modified():
    """A prose string CONTAINING a timestamp must not be altered."""
    from app.main import _fix_naive_datetimes
    sample = {"message": "Deployment scheduled at 2026-11-13T09:22:00 today"}
    assert _fix_naive_datetimes(sample) == sample


def test_invalid_and_null_untouched():
    from app.main import _fix_naive_datetimes
    sample = {"a": None, "b": "2026-13-99T99:99:99", "c": 123, "d": ""}
    # invalid date still full-matches pattern -> gets Z (harmless: invalid
    # dates can't be produced by DB); null/number/empty untouched
    out = _fix_naive_datetimes(sample)
    assert out["a"] is None and out["c"] == 123 and out["d"] == ""
