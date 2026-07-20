"""
Unit tests for the NexusCore Enterprise Security and Data Protection stack.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.main import app, orchestrator
from src.tools.orchestrator import Tool
from src.security import (
    pii_masker,
    data_protector,
    safe_math_evaluator,
    security_manager,
    API_KEY_NAME,
)


class TestPIIMasking:
    """Tests PII detection and redaction utilities."""

    def test_email_masking(self) -> None:
        text = "Contact support at help@nexuscore-enterprise.com immediately."
        expected = "Contact support at [REDACTED_EMAIL] immediately."
        assert pii_masker.mask(text) == expected

    def test_phone_masking(self) -> None:
        text = "Reach me at +1 (555) 019-2834 or 555-123-4567."
        masked = pii_masker.mask(text)
        assert "[REDACTED_PHONE]" in masked
        assert "555-123-4567" not in masked

    def test_ssn_masking(self) -> None:
        text = "Tax ID: 000-12-3456."
        assert pii_masker.mask(text) == "Tax ID: [REDACTED_SSN]."

    def test_credit_card_masking(self) -> None:
        text = "Card payment: 1234-5678-9012-3456."
        assert pii_masker.mask(text) == "Card payment: [REDACTED_CREDIT_CARD]."

    def test_api_key_and_secrets_masking(self) -> None:
        text = "My key is sk-proj-1234567890abcdef1234567890abcdef and secret is api_key='supersecretpassword123'."
        masked = pii_masker.mask(text)
        assert "sk-proj" not in masked
        assert "supersecretpassword123" not in masked
        assert "[REDACTED_OPENAI_KEY]" in masked
        assert "[REDACTED_GENERIC_SECRET]" in masked


class TestDataProtectionEncryption:
    """Tests AES-GCM data encryption and decryption."""

    def test_encrypt_decrypt_cycle(self) -> None:
        plaintext = "This is extremely sensitive configuration snapshot content."
        ciphertext = data_protector.encrypt(plaintext)
        assert ciphertext != plaintext
        assert len(ciphertext) > 0

        decrypted = data_protector.decrypt(ciphertext)
        assert decrypted == plaintext

    def test_iv_randomness(self) -> None:
        plaintext = "Constant string"
        cipher_1 = data_protector.encrypt(plaintext)
        cipher_2 = data_protector.encrypt(plaintext)
        # Random IV/nonce ensures ciphertext is different each execution
        assert cipher_1 != cipher_2

    def test_invalid_payloads(self) -> None:
        with pytest.raises(ValueError, match="Decryption failed"):
            data_protector.decrypt("invalid-base64-payload-12345")


class TestSafeMathEvaluation:
    """Tests Abstract Syntax Tree (AST) safe mathematical evaluator."""

    def test_safe_math_expression(self) -> None:
        assert safe_math_evaluator.evaluate("2 + 2") == 4
        assert safe_math_evaluator.evaluate("3 * (10 - 2) / 4") == 6.0
        assert safe_math_evaluator.evaluate("2 ** 8") == 256

    def test_unsafe_expression_raises_value_error(self) -> None:
        # Attempt to run builtins, print, imports, etc.
        with pytest.raises(ValueError, match="Unsafe or unsupported AST node"):
            safe_math_evaluator.evaluate("print('hello')")

        with pytest.raises(ValueError, match="Unsafe or unsupported AST node"):
            safe_math_evaluator.evaluate("__import__('os').system('ls')")

        with pytest.raises(ValueError, match="Unsafe constant type"):
            safe_math_evaluator.evaluate("'string_not_allowed'")

    def test_catastrophic_power_limit(self) -> None:
        with pytest.raises(ValueError, match="Power operation inputs exceed safe execution limits"):
            safe_math_evaluator.evaluate("2 ** 999999999")


class TestAuthorizationRBAC:
    """Tests hierarchical RBAC rules."""

    def test_role_hierarchy(self) -> None:
        # admin should be authorized for admin, operator, and viewer tasks
        assert security_manager.is_authorized("admin", "admin") is True
        assert security_manager.is_authorized("admin", "operator") is True
        assert security_manager.is_authorized("admin", "viewer") is True

        # operator should be authorized for operator and viewer, but not admin
        assert security_manager.is_authorized("operator", "admin") is False
        assert security_manager.is_authorized("operator", "operator") is True
        assert security_manager.is_authorized("operator", "viewer") is True

        # viewer should only be authorized for viewer
        assert security_manager.is_authorized("viewer", "admin") is False
        assert security_manager.is_authorized("viewer", "operator") is False
        assert security_manager.is_authorized("viewer", "viewer") is True


class TestAPIKeyEndpoints:
    """Integration/FastAPI tests with TestClient for security policy verification."""

    def setup_method(self) -> None:
        self.client = TestClient(app)

    def test_unauthenticated_requests(self) -> None:
        # Direct public endpoints work without key
        response = self.client.get("/health")
        assert response.status_code == 200

        # Protected endpoints return 401 Unauthorized
        response = self.client.get("/api/tools")
        assert response.status_code == 401
        assert "Missing API Key" in response.json()["detail"]

    def test_invalid_api_key(self) -> None:
        headers = {API_KEY_NAME: "wrong-key-123"}
        response = self.client.get("/api/tools", headers=headers)
        assert response.status_code == 403
        assert "Invalid API Key" in response.json()["detail"]

    def test_viewer_access(self) -> None:
        headers = {API_KEY_NAME: "nexus-viewer-secret-key"}
        # Can access viewer endpoints
        response = self.client.get("/api/tools", headers=headers)
        assert response.status_code == 200

        # Cannot access operator endpoints
        response = self.client.post("/api/tools/execute?name=calculator", headers=headers)
        assert response.status_code == 403

    def test_operator_access(self) -> None:
        headers = {API_KEY_NAME: "nexus-operator-secret-key"}
        # Can list tools
        response = self.client.get("/api/tools", headers=headers)
        assert response.status_code == 200

        # Can execute calculator tool
        response = self.client.post("/api/tools/execute?name=calculator", headers=headers)
        assert response.status_code == 200

        # Cannot take a snapshot (admin-only)
        response = self.client.post("/api/observability/rollback/snapshot", headers=headers)
        assert response.status_code == 403

    def test_admin_access(self) -> None:
        headers = {API_KEY_NAME: "nexus-admin-secret-key"}
        # Can list tools
        response = self.client.get("/api/tools", headers=headers)
        assert response.status_code == 200

        # Can take snapshot
        response = self.client.post("/api/observability/rollback/snapshot?description=TestSnap", headers=headers)
        assert response.status_code == 200
        assert "snapshot_id" in response.json()

    def test_dynamic_tool_permission_escalation_protection(self) -> None:
        # Register an admin-level test tool
        orchestrator.register_tool(
            Tool(
                name="secret_admin_tool",
                description="Requires admin role to run.",
                capabilities=["admin-secret"],
                permission_level="admin",
                fn=lambda: "Authorized Admin Run",
            )
        )

        try:
            # 1. Try to run it as Operator (Role: Operator) -> expect 403 Forbidden
            op_headers = {API_KEY_NAME: "nexus-operator-secret-key"}
            response = self.client.post("/api/tools/execute?name=secret_admin_tool", headers=op_headers)
            assert response.status_code == 403
            assert "Insufficient permissions" in response.json()["detail"]

            # 2. Try to run it as Admin (Role: Admin) -> expect 200 Success
            admin_headers = {API_KEY_NAME: "nexus-admin-secret-key"}
            response = self.client.post("/api/tools/execute?name=secret_admin_tool", headers=admin_headers)
            assert response.status_code == 200
            assert response.json()["output"] == "Authorized Admin Run"

        finally:
            # Unregister tool to clean up
            orchestrator.unregister_tool("secret_admin_tool")
