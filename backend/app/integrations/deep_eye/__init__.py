"""
Deep Eye integration package for KAWAL SIBER.
"""
from app.integrations.deep_eye.adapter import DeepEyeAdapter, deep_eye_adapter
from app.integrations.deep_eye.config import PROFILES, DEFAULT_ALLOWED_HOSTS
from app.integrations.deep_eye.validator import parse_and_validate_target_url, WebValidationError

__all__ = [
    "DeepEyeAdapter",
    "deep_eye_adapter",
    "PROFILES",
    "DEFAULT_ALLOWED_HOSTS",
    "parse_and_validate_target_url",
    "WebValidationError",
]

