"""
Tests for Security Configuration
Production validation, ALLOWED_HOSTS, and critical env var checks
"""

import os
import pytest
from unittest.mock import patch


# ==================== ALLOWED_HOSTS ====================

class TestAllowedHosts:

    def test_default_allowed_hosts_is_localhost(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ALLOWED_HOSTS", None)
            from app.core.simple_config import SimpleSettings
            s = SimpleSettings()
            assert s.ALLOWED_HOSTS == ["localhost"]

    def test_allowed_hosts_from_env_single(self):
        with patch.dict(os.environ, {"ALLOWED_HOSTS": "api.example.com"}):
            from app.core.simple_config import SimpleSettings
            s = SimpleSettings()
            assert s.ALLOWED_HOSTS == ["api.example.com"]

    def test_allowed_hosts_from_env_multiple(self):
        with patch.dict(os.environ, {"ALLOWED_HOSTS": "api.example.com, app.example.com"}):
            from app.core.simple_config import SimpleSettings
            s = SimpleSettings()
            assert s.ALLOWED_HOSTS == ["api.example.com", "app.example.com"]

    def test_allowed_hosts_strips_whitespace(self):
        with patch.dict(os.environ, {"ALLOWED_HOSTS": "  host1.com ,  host2.com  "}):
            from app.core.simple_config import SimpleSettings
            s = SimpleSettings()
            assert s.ALLOWED_HOSTS == ["host1.com", "host2.com"]

    def test_allowed_hosts_ignores_empty_entries(self):
        with patch.dict(os.environ, {"ALLOWED_HOSTS": "host1.com,,, host2.com,"}):
            from app.core.simple_config import SimpleSettings
            s = SimpleSettings()
            assert s.ALLOWED_HOSTS == ["host1.com", "host2.com"]


# ==================== Production Validation ====================

class TestProductionValidation:

    def _make_production_env(self, overrides=None):
        """Base env vars that satisfy all production checks."""
        env = {
            "ENVIRONMENT": "production",
            "JWT_SECRET_KEY": "a-really-long-production-secret-that-is-safe-abc123xyz",
            "POSTGRES_PASSWORD": "a-really-strong-db-password-abc123",
            "ALLOWED_HOSTS": "api.example.com",
            "BOOTSTRAP_ADMIN_PASSWORD": "SecureAdminP@ss1",
            "REDIS_URL": "redis://:secretpass@redis:6379/0",
        }
        if overrides:
            env.update(overrides)
        return env

    def test_production_valid_config_does_not_exit(self):
        env = self._make_production_env()
        with patch.dict(os.environ, env, clear=False):
            from app.core.simple_config import SimpleSettings
            s = SimpleSettings()
            assert s.ENVIRONMENT == "production"

    def test_production_rejects_default_jwt_secret(self):
        env = self._make_production_env({
            "JWT_SECRET_KEY": "your-super-secret-jwt-key-change-in-production-min-32-chars-for-security"
        })
        with patch.dict(os.environ, env, clear=False):
            from app.core.simple_config import SimpleSettings
            with pytest.raises(SystemExit):
                SimpleSettings()

    def test_production_rejects_empty_db_password(self):
        env = self._make_production_env({"POSTGRES_PASSWORD": ""})
        with patch.dict(os.environ, env, clear=False):
            from app.core.simple_config import SimpleSettings
            with pytest.raises(SystemExit):
                SimpleSettings()

    def test_production_rejects_default_db_password(self):
        env = self._make_production_env({"POSTGRES_PASSWORD": "iot_password"})
        with patch.dict(os.environ, env, clear=False):
            from app.core.simple_config import SimpleSettings
            with pytest.raises(SystemExit):
                SimpleSettings()

    def test_production_rejects_wildcard_allowed_hosts(self):
        env = self._make_production_env({"ALLOWED_HOSTS": "*"})
        with patch.dict(os.environ, env, clear=False):
            from app.core.simple_config import SimpleSettings
            with pytest.raises(SystemExit):
                SimpleSettings()

    def test_production_auto_generates_default_admin_password(self):
        env = self._make_production_env({"BOOTSTRAP_ADMIN_PASSWORD": "IotDevSim"})
        with patch.dict(os.environ, env, clear=False):
            from app.core.simple_config import SimpleSettings
            s = SimpleSettings()
            assert s.BOOTSTRAP_ADMIN_PASSWORD != "IotDevSim"
            assert len(s.BOOTSTRAP_ADMIN_PASSWORD) > 10

    def test_development_skips_validation(self):
        """In development, insecure defaults are fine."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=False):
            from app.core.simple_config import SimpleSettings
            s = SimpleSettings()
            assert s.ENVIRONMENT == "development"


# ==================== CORS Origins ====================

class TestCorsOrigins:

    def test_default_cors_origins(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CORS_ORIGINS", None)
            from app.core.simple_config import SimpleSettings
            s = SimpleSettings()
            assert s.CORS_ORIGINS == ["http://localhost:5173"]

    def test_multiple_cors_origins(self):
        with patch.dict(os.environ, {"CORS_ORIGINS": "http://a.com,http://b.com"}):
            from app.core.simple_config import SimpleSettings
            s = SimpleSettings()
            assert "http://a.com" in s.CORS_ORIGINS
            assert "http://b.com" in s.CORS_ORIGINS


# ==================== Rate Limit Config ====================

class TestRateLimitConfig:

    def test_default_rate_limit(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("RATE_LIMIT_PER_MINUTE", None)
            from app.core.simple_config import SimpleSettings
            s = SimpleSettings()
            assert s.RATE_LIMIT_PER_MINUTE == 60

    def test_custom_rate_limit(self):
        with patch.dict(os.environ, {"RATE_LIMIT_PER_MINUTE": "120"}):
            from app.core.simple_config import SimpleSettings
            s = SimpleSettings()
            assert s.RATE_LIMIT_PER_MINUTE == 120
