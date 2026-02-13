"""
Encryption utilities for sensitive data
Application-level encryption for connection credentials
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import json
from typing import Any, Dict
import structlog

from app.core.simple_config import settings

logger = structlog.get_logger()

# Sensitive field names that should be encrypted
SENSITIVE_FIELDS = {
    'password',
    'bearer_token',
    'api_key_value',
    'username',  # Encrypt username for extra security
    'ca_cert',
    'client_cert',
    'client_key',
    'ssl_ca_cert',
    'ssl_client_cert',
    'ssl_client_key',
}


class EncryptionService:
    """Service for encrypting and decrypting sensitive data"""
    
    def __init__(self):
        """Initialize encryption service with key derivation"""
        # Derive encryption key from JWT secret
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'iot-devsim-v2-salt',  # Static salt for consistent key derivation
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(settings.JWT_SECRET_KEY.encode()))
        self.cipher = Fernet(key)
    
    def encrypt_value(self, value: str) -> str:
        """
        Encrypt a single value
        
        Args:
            value: Plain text value to encrypt
        
        Returns:
            Encrypted value as base64 string
        """
        try:
            if not value:
                return value
            
            encrypted = self.cipher.encrypt(value.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error("Encryption failed", error=str(e))
            raise ValueError(f"Failed to encrypt value: {str(e)}")
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """
        Decrypt a single value
        
        Args:
            encrypted_value: Encrypted value as base64 string
        
        Returns:
            Decrypted plain text value
        """
        try:
            if not encrypted_value:
                return encrypted_value
            
            decrypted = self.cipher.decrypt(encrypted_value.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error("Decryption failed", error=str(e))
            raise ValueError(f"Failed to decrypt value: {str(e)}")
    
    def encrypt_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt sensitive fields in configuration dictionary
        
        Args:
            config: Configuration dictionary
        
        Returns:
            Configuration with encrypted sensitive fields
        """
        if not config:
            return config
        
        encrypted_config = config.copy()
        
        for field, value in config.items():
            if field in SENSITIVE_FIELDS and value:
                try:
                    encrypted_config[field] = self.encrypt_value(str(value))
                    logger.debug("Field encrypted", field=field)
                except Exception as e:
                    logger.error("Failed to encrypt field", field=field, error=str(e))
                    raise
        
        return encrypted_config
    
    def decrypt_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt sensitive fields in configuration dictionary
        
        Args:
            config: Configuration dictionary with encrypted fields
        
        Returns:
            Configuration with decrypted sensitive fields
        """
        if not config:
            return config
        
        decrypted_config = config.copy()
        
        for field, value in config.items():
            if field in SENSITIVE_FIELDS and value:
                try:
                    decrypted_config[field] = self.decrypt_value(str(value))
                    logger.debug("Field decrypted", field=field)
                except Exception as e:
                    logger.error("Failed to decrypt field", field=field, error=str(e))
                    # Return original value if decryption fails (might not be encrypted)
                    decrypted_config[field] = value
        
        return decrypted_config
    
    def encrypt_bytes(self, data: bytes) -> bytes:
        """
        Encrypt binary data (e.g., file contents) for encryption at rest.
        
        Args:
            data: Raw bytes to encrypt
        
        Returns:
            Encrypted bytes
        """
        try:
            return self.cipher.encrypt(data)
        except Exception as e:
            logger.error("Bytes encryption failed", error=str(e), size=len(data))
            raise ValueError(f"Failed to encrypt data: {str(e)}")

    def decrypt_bytes(self, encrypted_data: bytes) -> bytes:
        """
        Decrypt binary data (e.g., encrypted file contents).
        
        Args:
            encrypted_data: Encrypted bytes
        
        Returns:
            Decrypted raw bytes
        """
        try:
            return self.cipher.decrypt(encrypted_data)
        except Exception as e:
            logger.error("Bytes decryption failed", error=str(e))
            raise ValueError(f"Failed to decrypt data: {str(e)}")

    def mask_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mask sensitive fields in configuration for API responses
        
        Args:
            config: Configuration dictionary
        
        Returns:
            Configuration with masked sensitive fields
        """
        if not config:
            return config
        
        masked_config = config.copy()
        
        for field in SENSITIVE_FIELDS:
            if field in masked_config and masked_config[field]:
                # Mask with asterisks
                masked_config[field] = "********"
        
        return masked_config


# Global encryption service instance
encryption_service = EncryptionService()


def encrypt_connection_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Encrypt sensitive fields in connection configuration
    
    Args:
        config: Connection configuration
    
    Returns:
        Configuration with encrypted sensitive fields
    """
    return encryption_service.encrypt_config(config)


def decrypt_connection_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decrypt sensitive fields in connection configuration
    
    Args:
        config: Connection configuration with encrypted fields
    
    Returns:
        Configuration with decrypted sensitive fields
    """
    return encryption_service.decrypt_config(config)


def mask_connection_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mask sensitive fields in connection configuration for API responses
    
    Args:
        config: Connection configuration
    
    Returns:
        Configuration with masked sensitive fields
    """
    return encryption_service.mask_config(config)
