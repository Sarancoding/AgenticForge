"""
NexusCore Enterprise Security & Data Protection Package.
"""

from __future__ import annotations

from src.security.auth import (
    security_manager,
    verify_api_key,
    require_role,
    API_KEY_NAME,
)
from src.security.data_protection import (
    pii_masker,
    data_protector,
    PIIMasker,
    DataProtector,
)
from src.security.safe_eval import (
    safe_math_evaluator,
    SafeMathEvaluator,
)

__all__ = [
    "security_manager",
    "verify_api_key",
    "require_role",
    "API_KEY_NAME",
    "pii_masker",
    "data_protector",
    "PIIMasker",
    "DataProtector",
    "safe_math_evaluator",
    "SafeMathEvaluator",
]
