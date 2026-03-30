"""
Tests for Encryption Service
encrypt/decrypt values, configs, bytes, and masking
"""

import pytest

from app.core.encryption import (
    EncryptionService,
    SENSITIVE_FIELDS,
    encrypt_connection_config,
    decrypt_connection_config,
    mask_connection_config,
)


@pytest.fixture
def enc():
    return EncryptionService()


# ==================== Value Encryption ====================


class TestEncryptDecryptValue:

    def test_roundtrip(self, enc):
        plaintext = "my-secret-password"
        encrypted = enc.encrypt_value(plaintext)
        assert encrypted != plaintext
        assert enc.decrypt_value(encrypted) == plaintext

    def test_empty_string_passthrough(self, enc):
        assert enc.encrypt_value("") == ""
        assert enc.decrypt_value("") == ""

    def test_none_passthrough(self, enc):
        assert enc.encrypt_value(None) is None
        assert enc.decrypt_value(None) is None

    def test_different_ciphertexts_for_same_plaintext(self, enc):
        ct1 = enc.encrypt_value("same")
        ct2 = enc.encrypt_value("same")
        # Fernet uses a timestamp + IV so ciphertexts differ
        assert ct1 != ct2

    def test_decrypt_invalid_token_raises(self, enc):
        with pytest.raises(ValueError, match="Failed to decrypt"):
            enc.decrypt_value("not-a-valid-fernet-token")

    def test_unicode_roundtrip(self, enc):
        text = "contraseña-🔑-密码"
        assert enc.decrypt_value(enc.encrypt_value(text)) == text


# ==================== Config Encryption ====================


class TestEncryptDecryptConfig:

    def test_encrypts_sensitive_fields_only(self, enc):
        config = {
            "broker_url": "mqtt://broker.local",
            "port": 1883,
            "password": "secret123",
            "username": "admin",
        }
        encrypted = enc.encrypt_config(config)

        # Non-sensitive fields unchanged
        assert encrypted["broker_url"] == "mqtt://broker.local"
        assert encrypted["port"] == 1883

        # Sensitive fields encrypted
        assert encrypted["password"] != "secret123"
        assert encrypted["username"] != "admin"

    def test_config_roundtrip(self, enc):
        config = {"password": "s3cret", "ca_cert": "-----BEGIN CERT-----"}
        encrypted = enc.encrypt_config(config)
        decrypted = enc.decrypt_config(encrypted)

        assert decrypted["password"] == "s3cret"
        assert decrypted["ca_cert"] == "-----BEGIN CERT-----"

    def test_empty_config_passthrough(self, enc):
        assert enc.encrypt_config({}) == {}
        assert enc.encrypt_config(None) is None
        assert enc.decrypt_config({}) == {}
        assert enc.decrypt_config(None) is None

    def test_config_with_none_sensitive_values(self, enc):
        config = {"password": None, "broker_url": "mqtt://x"}
        encrypted = enc.encrypt_config(config)
        assert encrypted["password"] is None
        assert encrypted["broker_url"] == "mqtt://x"


# ==================== Bytes Encryption ====================


class TestEncryptDecryptBytes:

    def test_bytes_roundtrip(self, enc):
        data = b"binary-payload-\x00\xff"
        encrypted = enc.encrypt_bytes(data)
        assert encrypted != data
        assert enc.decrypt_bytes(encrypted) == data

    def test_empty_bytes(self, enc):
        encrypted = enc.encrypt_bytes(b"")
        assert enc.decrypt_bytes(encrypted) == b""

    def test_decrypt_invalid_bytes_raises(self, enc):
        with pytest.raises(ValueError, match="Failed to decrypt"):
            enc.decrypt_bytes(b"garbage")


# ==================== Config Masking ====================


class TestMaskConfig:

    def test_masks_sensitive_fields(self, enc):
        config = {
            "password": "secret",
            "bearer_token": "tok123",
            "broker_url": "mqtt://x",
        }
        masked = enc.mask_config(config)

        assert masked["password"] == "********"
        assert masked["bearer_token"] == "********"
        assert masked["broker_url"] == "mqtt://x"

    def test_none_sensitive_values_not_masked(self, enc):
        config = {"password": None, "broker_url": "mqtt://x"}
        masked = enc.mask_config(config)
        assert masked["password"] is None

    def test_empty_config(self, enc):
        assert enc.mask_config({}) == {}
        assert enc.mask_config(None) is None


# ==================== Module-level helpers ====================


class TestModuleLevelHelpers:

    def test_encrypt_connection_config(self):
        config = {"password": "pw", "port": 1883}
        result = encrypt_connection_config(config)
        assert result["password"] != "pw"
        assert result["port"] == 1883

    def test_decrypt_connection_config(self):
        config = {"password": "pw", "port": 1883}
        encrypted = encrypt_connection_config(config)
        decrypted = decrypt_connection_config(encrypted)
        assert decrypted["password"] == "pw"

    def test_mask_connection_config(self):
        config = {"password": "pw", "port": 1883}
        masked = mask_connection_config(config)
        assert masked["password"] == "********"
        assert masked["port"] == 1883


# ==================== SENSITIVE_FIELDS constant ====================


class TestSensitiveFieldsConstant:

    def test_contains_expected_fields(self):
        expected = {"password", "bearer_token", "api_key_value", "username", "ca_cert", "client_key"}
        assert expected.issubset(SENSITIVE_FIELDS)
