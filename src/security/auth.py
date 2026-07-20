"""
Authentication and Role-Based Access Control (RBAC) implementation.
Provides FastAPI dependencies to protect endpoints based on user roles and API Keys.
"""

from __future__ import annotations

import json
import os
import logging
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader

logger = logging.getLogger(__name__)

API_KEY_NAME = "X-NexusCore-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Preconfigured default API keys for roles: admin, operator, viewer
DEFAULT_KEYS = {
    "nexus-admin-secret-key": "admin",
    "nexus-operator-secret-key": "operator",
    "nexus-viewer-secret-key": "viewer",
}

def load_api_keys() -> dict[str, str]:
    """Load API keys mapping from environment or use default development keys."""
    env_keys = os.getenv("NEXUSCORE_API_KEYS")
    if env_keys:
        try:
            return json.loads(env_keys)
        except Exception as e:
            logger.error("Failed to parse NEXUSCORE_API_KEYS environment variable: %s", e)

    # Prominent warning when running on default development fallback keys
    logger.warning(
        "⚠️ WARNING: Running with default development API keys. "
        "For production, configure the 'NEXUSCORE_API_KEYS' environment variable."
    )
    return DEFAULT_KEYS

class SecurityManager:
    """Manager for loading keys and validating user access permissions."""

    def __init__(self) -> None:
        self.api_keys = load_api_keys()

    def get_role_for_key(self, api_key: str) -> str | None:
        """Retrieve the associated role for a given API key."""
        return self.api_keys.get(api_key)

    def is_authorized(self, user_role: str, required_role: str) -> bool:
        """
        Check if the user_role meets or exceeds the required_role level.
        Role hierarchy: admin > operator > viewer
        """
        hierarchy = {"viewer": 0, "operator": 1, "admin": 2}
        user_level = hierarchy.get(user_role.lower(), -1)
        req_level = hierarchy.get(required_role.lower(), 99)
        return user_level >= req_level


# Global instance
security_manager = SecurityManager()


async def verify_api_key(key: str | None = Security(api_key_header)) -> str:
    """FastAPI dependency to verify API Key existence and return its associated role."""
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing API Key. Please provide the '{API_KEY_NAME}' header.",
        )
    role = security_manager.get_role_for_key(key)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key. Access denied.",
        )
    return role


def require_role(required_role: str):
    """
    FastAPI dependency factory to enforce Role-Based Access Control.
    Example: Depends(require_role("operator"))
    """
    async def dependency(role: str = Security(verify_api_key)) -> str:
        if not security_manager.is_authorized(role, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}, current role: {role}",
            )
        return role
    return dependency
