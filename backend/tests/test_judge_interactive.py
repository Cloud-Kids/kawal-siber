"""
Tests for judge_mode.py interactive mode enforcement.
Tests write authorization, rate limiting, concurrency limits, and target validation.
"""
import os
import pytest
from unittest.mock import Mock, patch
from fastapi import Request
from fastapi.responses import JSONResponse

# Set interactive mode for tests
os.environ["KAWAL_JUDGE_MODE"] = "interactive"

from app.judge_mode import (
    judge_guard,
    JUDGE_INTERACTIVE,
    _is_write_allowed,
    _validate_target_url,
    _rate_limited,
    _check_concurrency_limit,
    _increment_concurrency,
    _decrement_concurrency,
)


class TestJudgeModeDetection:
    """Test judge mode detection."""
    
    def test_interactive_mode_detection(self):
        """Test that interactive mode is correctly detected."""
        assert JUDGE_INTERACTIVE is True


class TestWriteAuthorization:
    """Test write operation authorization."""
    
    def test_asset_create_allowed(self):
        """Test that asset creation is allowed."""
        allowed, resource_type = _is_write_allowed("POST", "/api/v1/assets")
        assert allowed is True
        assert resource_type == "asset_create"
    
    def test_asset_update_allowed(self):
        """Test that asset update is allowed."""
        allowed, resource_type = _is_write_allowed("PATCH", "/api/v1/assets/1")
        assert allowed is True
        assert resource_type == "asset_update"
    
    def test_asset_delete_allowed(self):
        """Test that asset deletion is allowed."""
        allowed, resource_type = _is_write_allowed("DELETE", "/api/v1/assets/1")
        assert allowed is True
        assert resource_type == "asset_delete"
    
    def test_web_target_create_allowed(self):
        """Test that web target creation is allowed."""
        allowed, resource_type = _is_write_allowed("POST", "/api/v1/web-targets")
        assert allowed is True
        assert resource_type == "web_target_create"
    
    def test_web_assessment_create_allowed(self):
        """Test that web assessment creation is allowed."""
        allowed, resource_type = _is_write_allowed("POST", "/api/v1/web-assessments")
        assert allowed is True
        assert resource_type == "web_assessment_create"
    
    def test_incident_create_allowed(self):
        """Test that incident creation is allowed."""
        allowed, resource_type = _is_write_allowed("POST", "/api/v1/incidents")
        assert allowed is True
        assert resource_type == "incident_create"
    
    def test_incident_triage_allowed(self):
        """Test that incident triage is allowed."""
        allowed, resource_type = _is_write_allowed("POST", "/api/v1/incidents/1/triage")
        assert allowed is True
        assert resource_type == "incident_action"
    
    def test_report_create_allowed(self):
        """Test that report creation is allowed."""
        allowed, resource_type = _is_write_allowed("POST", "/api/v1/reports")
        assert allowed is True
        assert resource_type == "report_create"
    
    def test_report_regenerate_allowed(self):
        """Test that report regeneration is allowed."""
        allowed, resource_type = _is_write_allowed("POST", "/api/v1/reports/123/regenerate")
        assert allowed is True
        assert resource_type == "report_action"
    
    def test_pcap_upload_allowed(self):
        """Test that PCAP upload is allowed."""
        allowed, resource_type = _is_write_allowed("POST", "/api/v1/monitoring/pcap")
        assert allowed is True
        assert resource_type == "pcap_upload"
    
    def test_scan_create_allowed(self):
        """Test that scan creation is allowed for assets."""
        allowed, resource_type = _is_write_allowed("POST", "/api/v1/assets/1/scans")
        assert allowed is True
        assert resource_type == "scan_create"
    
    def test_admin_write_denied(self):
        """Test that admin write operations are denied."""
        allowed, resource_type = _is_write_allowed("POST", "/api/v1/admin/users")
        assert allowed is False
        assert resource_type is None
    
    def test_arbitrary_write_denied(self):
        """Test that arbitrary write operations are denied."""
        allowed, resource_type = _is_write_allowed("POST", "/api/v1/unknown")
        assert allowed is False
        assert resource_type is None


class TestTargetValidation:
    """Test target URL validation for synthetic target only."""
    
    def test_synthetic_target_allowed(self):
        """Test that synthetic target is allowed."""
        assert _validate_target_url("http://synthetic-target:8080") is True
        assert _validate_target_url("http://synthetic-target:8080/") is True
    
    def test_localhost_denied(self):
        """Test that localhost is denied."""
        assert _validate_target_url("http://localhost:8000") is False
        assert _validate_target_url("http://127.0.0.1:8000") is False
    
    def test_external_url_denied(self):
        """Test that external URLs are denied."""
        assert _validate_target_url("http://example.com") is False
        assert _validate_target_url("https://google.com") is False
    
    def test_private_ip_denied(self):
        """Test that private IPs are denied."""
        assert _validate_target_url("http://192.168.1.1") is False
        assert _validate_target_url("http://10.0.0.1") is False


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_read_rate_limit(self):
        """Test read rate limiting."""
        ip = "192.168.1.100"
        # Clear any existing hits
        from app.judge_mode import _hits_read
        _hits_read[ip].clear()
        
        # Should not be limited initially
        assert _rate_limited(ip, "read") is False
        
        # Simulate many requests
        for _ in range(120):
            _rate_limited(ip, "read")
        
        # Should be limited now
        assert _rate_limited(ip, "read") is True
    
    def test_write_rate_limit(self):
        """Test write rate limiting."""
        ip = "192.168.1.101"
        # Clear any existing hits
        from app.judge_mode import _hits_write
        _hits_write[ip].clear()
        
        # Should not be limited initially
        assert _rate_limited(ip, "write") is False
        
        # Simulate many write requests
        for _ in range(30):
            _rate_limited(ip, "write")
        
        # Should be limited now
        assert _rate_limited(ip, "write") is True
    
    def test_assessment_rate_limit(self):
        """Test assessment rate limiting."""
        ip = "192.168.1.102"
        # Clear any existing hits
        from app.judge_mode import _hits_assessment
        _hits_assessment[ip].clear()
        
        # Should not be limited initially
        assert _rate_limited(ip, "assessment") is False
        
        # Simulate many assessment requests
        for _ in range(10):
            _rate_limited(ip, "assessment")
        
        # Should be limited now
        assert _rate_limited(ip, "assessment") is True


class TestConcurrencyLimits:
    """Test concurrency limit functionality."""
    
    def test_assessment_concurrency_limit(self):
        """Test assessment concurrency limit."""
        ip = "192.168.1.200"
        # Clear any existing counts
        from app.judge_mode import _active_assessments
        _active_assessments[ip] = 0
        
        # Should not be limited initially
        assert _check_concurrency_limit("web_assessment_create", ip) is False
        
        # Increment to max
        for _ in range(3):
            _increment_concurrency("web_assessment_create", ip)
        
        # Should be limited now
        assert _check_concurrency_limit("web_assessment_create", ip) is True
        
        # Decrement one
        _decrement_concurrency("web_assessment_create", ip)
        
        # Should not be limited now
        assert _check_concurrency_limit("web_assessment_create", ip) is False
    
    def test_report_concurrency_limit(self):
        """Test report concurrency limit."""
        ip = "192.168.1.201"
        # Clear any existing counts
        from app.judge_mode import _active_reports
        _active_reports[ip] = 0
        
        # Should not be limited initially
        assert _check_concurrency_limit("report_create", ip) is False
        
        # Increment to max
        for _ in range(2):
            _increment_concurrency("report_create", ip)
        
        # Should be limited now
        assert _check_concurrency_limit("report_create", ip) is True


class TestJudgeGuard:
    """Test the main judge_guard function."""
    
    def create_mock_request(self, method: str, path: str, headers: dict = None):
        """Create a mock request object."""
        request = Mock(spec=Request)
        request.method = method
        request.url.path = path
        request.headers = headers or {}
        request.client.host = "192.168.1.1"
        return request
    
    def test_get_request_allowed(self):
        """Test that GET requests are allowed."""
        request = self.create_mock_request("GET", "/api/v1/assets")
        result = judge_guard(request)
        assert result is None
    
    def test_post_asset_allowed(self):
        """Test that POST to assets is allowed in interactive mode."""
        request = self.create_mock_request("POST", "/api/v1/assets")
        result = judge_guard(request)
        assert result is None
    
    def test_post_admin_denied(self):
        """Test that POST to admin is denied."""
        request = self.create_mock_request("POST", "/api/v1/admin/users")
        result = judge_guard(request)
        assert result is not None
        assert result.status_code == 403
    
    def test_docs_disabled(self):
        """Test that docs endpoints are disabled."""
        request = self.create_mock_request("GET", "/docs")
        result = judge_guard(request)
        assert result is not None
        assert result.status_code == 403
    
    def test_report_download_uuid_required(self):
        """Test that report download requires UUID."""
        request = self.create_mock_request("GET", "/api/v1/reports/123/download")
        result = judge_guard(request)
        assert result is not None
        assert result.status_code == 403
    
    def test_request_size_limit(self):
        """Test that request size limit is enforced."""
        request = self.create_mock_request(
            "POST", "/api/v1/assets",
            headers={"content-length": str(11 * 1024 * 1024)}  # 11MB > 10MB limit
        )
        result = judge_guard(request)
        assert result is not None
        assert result.status_code == 413


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
