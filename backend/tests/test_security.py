import pytest
from flask import Flask

from app import app
from core.app_support import configure_app, is_allowed_cors_origin
from database.token_crypto import decrypt_token_data, encrypt_token_data


def test_oauth_tokens_are_encrypted(monkeypatch):
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "test-only-encryption-key")
    source = {"access_token": "secret", "refresh_token": "more-secret"}

    encrypted = encrypt_token_data(source)

    assert "secret" not in encrypted
    assert decrypt_token_data(encrypted) == source


def test_tampered_oauth_token_is_rejected(monkeypatch):
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "test-only-encryption-key")
    encrypted = encrypt_token_data({"refresh_token": "secret"})

    with pytest.raises(RuntimeError, match="could not be decrypted"):
        decrypt_token_data(encrypted[:-2] + "xx")


def test_untrusted_browser_origin_cannot_mutate():
    with app.test_client() as client:
        response = client.post("/api/auth/logout", headers={"Origin": "https://evil.example"})

    assert response.status_code == 403


def test_api_responses_include_security_headers():
    with app.test_client() as client:
        response = client.get("/api/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "no-store"


def test_production_rejects_weak_security_config(monkeypatch):
    monkeypatch.setenv("PUBLIC_BACKEND_URL", "https://api.example.com")
    monkeypatch.setenv("FLASK_SECRET_KEY", "change-me")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "change-me-too")
    monkeypatch.setenv("AUTOMATION_SECRET", "replace-me")
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://app.example.com")

    with pytest.raises(RuntimeError, match="Unsafe production configuration"):
        configure_app(Flask("unsafe-production-test"))


def test_production_does_not_trust_localhost_origins(monkeypatch):
    monkeypatch.setenv("PUBLIC_BACKEND_URL", "https://api.example.com")
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://app.example.com")

    assert is_allowed_cors_origin("https://app.example.com") is True
    assert is_allowed_cors_origin("http://localhost:5173") is False


def test_production_token_encryption_requires_dedicated_key(monkeypatch):
    monkeypatch.setenv("PUBLIC_BACKEND_URL", "https://api.example.com")
    monkeypatch.delenv("TOKEN_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("FLASK_SECRET_KEY", "a-valid-but-separate-session-secret")

    with pytest.raises(RuntimeError, match="TOKEN_ENCRYPTION_KEY is required"):
        encrypt_token_data({"refresh_token": "secret"})
