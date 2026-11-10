"""
test_scope_validator.py — Unit tests for worker scope validator and DNS rebinding protections.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from worker.scope_validator import (
    DNSResolutionError,
    OutOfScopeError,
    ScopeDisabledError,
    ScopeExpiredError,
    ScopeValidationError,
    check_ip_in_cidr,
    validate_scope_active,
    validate_target_against_scope,
)


def test_check_ip_in_cidr():
    assert check_ip_in_cidr("192.168.1.50", "192.168.1.0/24") is True
    assert check_ip_in_cidr("192.168.2.50", "192.168.1.0/24") is False
    assert check_ip_in_cidr("10.0.0.1", "10.0.0.0/8") is True
    assert check_ip_in_cidr("fe80::1", "fe80::/64") is True

    with pytest.raises(ScopeValidationError):
        check_ip_in_cidr("invalid-ip", "10.0.0.0/8")


def test_validate_scope_active_lifecycle():
    now = datetime.now(timezone.utc)
    future = now + timedelta(days=5)
    past = now - timedelta(days=1)

    # Valid active scope
    validate_scope_active(enabled=True, expires_at=future)

    # Disabled scope
    with pytest.raises(ScopeDisabledError):
        validate_scope_active(enabled=False, expires_at=future)

    # Expired scope
    with pytest.raises(ScopeExpiredError):
        validate_scope_active(enabled=True, expires_at=past)


def test_validate_target_direct_ip():
    future = datetime.now(timezone.utc) + timedelta(days=1)

    # In scope
    resolved = validate_target_against_scope(
        target="192.168.1.100",
        cidr="192.168.1.0/24",
        enabled=True,
        expires_at=future,
    )
    assert resolved == "192.168.1.100"

    # Out of scope
    with pytest.raises(OutOfScopeError):
        validate_target_against_scope(
            target="172.16.0.1",
            cidr="192.168.1.0/24",
            enabled=True,
            expires_at=future,
        )


def test_validate_target_hostname_and_dns_rebinding_protection():
    future = datetime.now(timezone.utc) + timedelta(days=1)

    # 1. Normal safe hostname where all records match scope
    with patch(
        "worker.scope_validator.resolve_hostname_all_ips",
        return_value=["10.0.1.5", "10.0.1.6"],
    ):
        resolved = validate_target_against_scope(
            target="app.lab.internal",
            cidr="10.0.0.0/16",
            enabled=True,
            expires_at=future,
        )
        assert resolved == "10.0.1.5"

    # 2. DNS Rebinding / Dual-homed attack: one IP inside scope, one IP outside
    with patch(
        "worker.scope_validator.resolve_hostname_all_ips",
        return_value=["10.0.1.5", "203.0.113.50"],  # 203.0.113.50 is public/unauthorized
    ):
        with pytest.raises(OutOfScopeError) as exc_info:
            validate_target_against_scope(
                target="sneaky.domain.internal",
                cidr="10.0.0.0/16",
                enabled=True,
                expires_at=future,
            )
        assert "203.0.113.50" in str(exc_info.value)

    # 3. Hostname cannot be resolved
    with patch(
        "worker.scope_validator.resolve_hostname_all_ips",
        side_effect=DNSResolutionError("Domain does not exist"),
    ):
        with pytest.raises(DNSResolutionError):
            validate_target_against_scope(
                target="nonexistent.internal",
                cidr="10.0.0.0/16",
                enabled=True,
                expires_at=future,
            )

