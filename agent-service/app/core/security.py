"""
JWT Validation for Agent Service
Uses joserfc (replaces python-jose due to CVE-2024-33663).
Same JWT_SECRET_KEY as api-service.
"""

import time
import structlog
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from joserfc import jwt
from joserfc.jwk import OctKey
from joserfc.errors import JoseError

from app.core.config import settings

logger = structlog.get_logger()

security_scheme = HTTPBearer()


class TokenPayload:
    """Parsed JWT token payload."""

    def __init__(self, sub: str, exp: int, iss: Optional[str] = None):
        self.sub = sub  # user_id
        self.exp = exp
        self.iss = iss


def decode_access_token(token: str) -> TokenPayload:
    """
    Decode and validate a JWT access token.
    Raises HTTPException if the token is invalid or expired.
    """
    try:
        key = OctKey.import_key(settings.JWT_SECRET_KEY)
        decoded = jwt.decode(
            token,
            key,
            algorithms=[settings.JWT_ALGORITHM],
        )
        claims = decoded.claims

        # Check expiration
        exp = claims.get("exp")
        if exp and time.time() > exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )

        sub = claims.get("sub")
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject claim",
            )

        return TokenPayload(
            sub=str(sub),
            exp=exp or 0,
            iss=claims.get("iss"),
        )

    except JoseError as e:
        logger.warning("JWT validation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error during token validation", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> TokenPayload:
    """
    FastAPI dependency: extract and validate the JWT from the Authorization header.
    Returns the decoded token payload with user_id in .sub.
    """
    return decode_access_token(credentials.credentials)
