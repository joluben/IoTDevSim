"""
Tests for Output Filter — Sensitive Data Sanitization.
Verifies that credentials, keys, tokens, and PII are redacted from SSE output.
"""

import pytest

from app.agent.security.output_filter import filter_output


class TestJWTTokenFiltering:
    def test_redacts_jwt_token(self):
        text = "Tu token es eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        result = filter_output(text)
        assert "eyJ" not in result
        assert "[REDACTED]" in result

    def test_preserves_text_around_jwt(self):
        text = "Hola, esto es texto normal sin tokens."
        assert filter_output(text) == text


class TestAPIKeyFiltering:
    def test_redacts_openai_key(self):
        text = "La clave es sk-proj-abc123def456ghi789jkl012mno"
        result = filter_output(text)
        assert "sk-proj" not in result
        assert "[REDACTED]" in result

    def test_redacts_anthropic_key(self):
        text = "Usar sk-ant-api03-abc123def456ghi789jkl012mno345pqr678stu"
        result = filter_output(text)
        assert "sk-ant" not in result

    def test_redacts_generic_api_key(self):
        text = 'config: api_key="abcdefghij1234567890klmnopqrst"'
        result = filter_output(text)
        assert "abcdefghij1234567890" not in result


class TestPrivateKeyFiltering:
    def test_redacts_private_key(self):
        text = """Aquí está la clave:
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA2Z3qX2BTLS4e...
-----END RSA PRIVATE KEY-----
No la compartas."""
        result = filter_output(text)
        assert "BEGIN RSA PRIVATE KEY" not in result
        assert "[REDACTED]" in result
        assert "No la compartas" in result

    def test_redacts_ec_private_key(self):
        text = "-----BEGIN EC PRIVATE KEY-----\nMHQCAQEE...\n-----END EC PRIVATE KEY-----"
        result = filter_output(text)
        assert "BEGIN EC PRIVATE KEY" not in result


class TestCertificateFiltering:
    def test_redacts_certificate(self):
        text = "Cert: -----BEGIN CERTIFICATE-----\nMIIBxTCCAW...\n-----END CERTIFICATE-----"
        result = filter_output(text)
        assert "BEGIN CERTIFICATE" not in result
        assert "[REDACTED]" in result


class TestPasswordFiltering:
    def test_redacts_password_in_config(self):
        text = 'La configuración tiene password: MySuperSecret123!'
        result = filter_output(text)
        assert "MySuperSecret123" not in result

    def test_redacts_json_style_password(self):
        text = '"password": "hunter2secret"'
        result = filter_output(text)
        assert "hunter2secret" not in result

    def test_redacts_secret_value(self):
        text = "secret=my_very_secret_value_12345"
        result = filter_output(text)
        assert "my_very_secret_value" not in result


class TestConnectionStringFiltering:
    def test_redacts_postgres_connection(self):
        text = "Conéctate a postgres://admin:p4ssw0rd@db.example.com:5432/mydb"
        result = filter_output(text)
        assert "p4ssw0rd" not in result
        assert "***:***@" in result

    def test_redacts_redis_connection(self):
        text = "redis://user:secret123@redis.local:6379"
        result = filter_output(text)
        assert "secret123" not in result

    def test_redacts_mqtt_connection(self):
        text = "mqtt://device:token123@broker.iot.com:1883"
        result = filter_output(text)
        assert "token123" not in result


class TestEmailFiltering:
    def test_redacts_email(self):
        text = "El usuario admin@company.com tiene acceso"
        result = filter_output(text)
        assert "admin@company.com" not in result
        assert "[REDACTED]" in result

    def test_preserves_non_email_at(self):
        text = "Usa @menciones en el chat"
        assert filter_output(text) == text


class TestAWSKeyFiltering:
    def test_redacts_aws_access_key(self):
        text = "AWS Key: AKIAIOSFODNN7EXAMPLE"
        result = filter_output(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in result


class TestNoFalsePositives:
    """Normal agent output should pass through unchanged."""

    @pytest.mark.parametrize("text", [
        "✅ Conexión creada: **MQTT Local** (`abc-123`) — protocolo: mqtt",
        "📊 **Datasets** (3 total):\n- ✅ **Temperaturas** (generated, 1000 filas)",
        "📱 **Dispositivos** (5 total):\n- ✅ **Sensor A** (sensor, ref: `DEV-001`)",
        "📈 **Análisis de tendencias** (últimas 50 entradas):\n- Exitosos: 45 (90.0%)",
        "🟢 Excelente\n**Volumen**\n- Total mensajes: 10,000",
        "No se encontraron conexiones.",
        "",
    ])
    def test_normal_output_unchanged(self, text):
        assert filter_output(text) == text
