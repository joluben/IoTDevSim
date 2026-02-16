"""
Security utilities for JWT authentication and password hashing
"""

from datetime import datetime, timedelta
from typing import Optional, Union, Any
from joserfc import jwt as jose_jwt
from joserfc.jwk import OctKey
from joserfc.errors import BadSignatureError, DecodeError, ExpiredTokenError, InvalidTokenError
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher
from fastapi import HTTPException, status
import structlog

from app.core.simple_config import settings
from app.core.token_validator import IssuerAwareTokenValidator, LocalJWTValidationStrategy

logger = structlog.get_logger()

# Password hashing context (pwdlib replaces abandoned passlib)
pwd_context = PasswordHash((BcryptHasher(),))

# JWT Configuration
ALGORITHM = settings.JWT_ALGORITHM
SECRET_KEY = settings.JWT_SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS

# joserfc key object (reusable)
_jwt_key = OctKey.import_key(SECRET_KEY)

_token_validator = IssuerAwareTokenValidator(
    active_issuer=settings.AUTH_ACTIVE_ISSUER,
    trusted_issuers=settings.AUTH_TRUSTED_ISSUERS,
    local_strategy=LocalJWTValidationStrategy(
        secret_key=SECRET_KEY,
        algorithm=ALGORITHM,
        issuer=settings.AUTH_LOCAL_ISSUER,
    ),
)


def create_access_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict] = None
) -> str:
    """
    Create JWT access token
    
    Args:
        subject: Token subject (usually user ID)
        expires_delta: Custom expiration time
        additional_claims: Additional claims to include in token
    
    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": int(expire.timestamp()),
        "sub": str(subject),
        "type": "access",
        "iat": int(datetime.utcnow().timestamp())
    }
    
    # Add additional claims if provided
    if additional_claims:
        to_encode.update(additional_claims)
    
    encoded_jwt = jose_jwt.encode({"alg": ALGORITHM}, to_encode, _jwt_key)
    
    logger.debug("Access token created", subject=subject, expires=expire)
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT refresh token
    
    Args:
        subject: Token subject (usually user ID)
        expires_delta: Custom expiration time
    
    Returns:
        Encoded JWT refresh token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "exp": int(expire.timestamp()),
        "sub": str(subject),
        "type": "refresh",
        "iat": int(datetime.utcnow().timestamp())
    }
    
    encoded_jwt = jose_jwt.encode({"alg": ALGORITHM}, to_encode, _jwt_key)
    
    logger.debug("Refresh token created", subject=subject, expires=expire)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[str]:
    """
    Verify JWT token and return subject
    
    Args:
        token: JWT token to verify
        token_type: Expected token type ('access' or 'refresh')
    
    Returns:
        Token subject if valid, None otherwise
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    result = _token_validator.validate(token, token_type=token_type)
    return result.subject


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database
    
    Returns:
        True if password matches, False otherwise
    """
    try:
        result = pwd_context.verify(plain_password, hashed_password)
        logger.debug("Password verification", result=result)
        return result
    except Exception as e:
        logger.error("Password verification error", error=str(e))
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password
    """
    try:
        # Bcrypt has a 72 byte limit, truncate if necessary
        # Using UTF-8 encoding to ensure proper byte count
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            password = password_bytes[:72].decode('utf-8', errors='ignore')
            logger.warning("Password truncated to 72 bytes for bcrypt")
        
        hashed = pwd_context.hash(password)
        logger.debug("Password hashed successfully")
        return hashed
    except Exception as e:
        logger.error("Password hashing error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing password"
        )


def generate_password_reset_token(email: str) -> str:
    """
    Generate password reset token
    
    Args:
        email: User email
    
    Returns:
        Password reset token
    """
    delta = timedelta(hours=1)  # Reset token expires in 1 hour
    now = datetime.utcnow()
    expires = now + delta
    
    to_encode = {
        "exp": int(expires.timestamp()),
        "sub": email,
        "type": "password_reset",
        "iat": int(now.timestamp())
    }
    
    encoded_jwt = jose_jwt.encode({"alg": ALGORITHM}, to_encode, _jwt_key)
    
    logger.info("Password reset token generated", email=email, expires=expires)
    return encoded_jwt


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verify password reset token
    
    Args:
        token: Password reset token
    
    Returns:
        Email if token is valid, None otherwise
    """
    try:
        token_obj = jose_jwt.decode(token, _jwt_key, algorithms=[ALGORITHM])
        payload = token_obj.claims
        
        # Check token type
        if payload.get("type") != "password_reset":
            logger.warning("Invalid password reset token type")
            return None
        
        email: str = payload.get("sub")
        if email is None:
            logger.warning("Password reset token missing email")
            return None
        
        logger.info("Password reset token verified", email=email)
        return email
        
    except (BadSignatureError, DecodeError, ExpiredTokenError, InvalidTokenError, ValueError) as e:
        logger.warning("Password reset token verification failed", error=str(e))
        return None


def create_api_key(user_id: str, name: str, expires_days: int = 365) -> str:
    """
    Create API key for external service authentication
    
    Args:
        user_id: User ID
        name: API key name/description
        expires_days: Expiration in days
    
    Returns:
        API key token
    """
    expire = datetime.utcnow() + timedelta(days=expires_days)
    
    to_encode = {
        "exp": int(expire.timestamp()),
        "sub": user_id,
        "type": "api_key",
        "name": name,
        "iat": int(datetime.utcnow().timestamp())
    }
    
    encoded_jwt = jose_jwt.encode({"alg": ALGORITHM}, to_encode, _jwt_key)
    
    logger.info("API key created", user_id=user_id, name=name, expires=expire)
    return encoded_jwt


def verify_api_key(token: str) -> Optional[dict]:
    """
    Verify API key
    
    Args:
        token: API key token
    
    Returns:
        Token payload if valid, None otherwise
    """
    try:
        token_obj = jose_jwt.decode(token, _jwt_key, algorithms=[ALGORITHM])
        payload = token_obj.claims
        
        # Check token type
        if payload.get("type") != "api_key":
            logger.warning("Invalid API key token type")
            return None
        
        user_id = payload.get("sub")
        name = payload.get("name")
        
        if not user_id:
            logger.warning("API key missing user ID")
            return None
        
        logger.debug("API key verified", user_id=user_id, name=name)
        return payload
        
    except (BadSignatureError, DecodeError, ExpiredTokenError, InvalidTokenError, ValueError) as e:
        logger.warning("API key verification failed", error=str(e))
        return None