"""
Token validation seam for future issuer-based auth strategies.

Phase 1 keeps local JWT issuer as active strategy.
Phase 2 can register external strategies (e.g. Keycloak) without changing call sites.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from joserfc import jwt as jose_jwt
from joserfc.jwk import OctKey
from joserfc.errors import BadSignatureError, DecodeError, ExpiredTokenError, InvalidTokenError
import structlog

logger = structlog.get_logger()


@dataclass(frozen=True)
class TokenValidationResult:
    subject: str
    claims: dict
    issuer: str


class TokenValidationStrategy(ABC):
    @abstractmethod
    def validate(self, token: str, token_type: str = "access") -> TokenValidationResult:
        raise NotImplementedError


class LocalJWTValidationStrategy(TokenValidationStrategy):
    def __init__(self, secret_key: str, algorithm: str, issuer: str) -> None:
        self._jwt_key = OctKey.import_key(secret_key)
        self._algorithm = algorithm
        self._issuer = issuer

    def validate(self, token: str, token_type: str = "access") -> TokenValidationResult:
        try:
            token_obj = jose_jwt.decode(token, self._jwt_key, algorithms=[self._algorithm])
            payload = token_obj.claims

            if payload.get("type") != token_type:
                logger.warning("Invalid token type", expected=token_type, actual=payload.get("type"))
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            subject = payload.get("sub")
            if subject is None:
                logger.warning("Token missing subject")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing subject",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            exp = payload.get("exp")
            if exp and datetime.utcnow() > datetime.fromtimestamp(exp):
                logger.warning("Token expired", subject=subject)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            issuer = payload.get("iss") or self._issuer
            logger.debug("Token verified successfully", subject=subject, issuer=issuer, type=token_type)
            return TokenValidationResult(subject=str(subject), claims=dict(payload), issuer=issuer)

        except (BadSignatureError, DecodeError, ExpiredTokenError, InvalidTokenError, ValueError) as exc:
            logger.warning("JWT verification failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )


class IssuerAwareTokenValidator:
    """
    Strategy router for token validation by issuer.

    In Phase 1, local strategy is the only active validator.
    """

    def __init__(
        self,
        *,
        active_issuer: str,
        trusted_issuers: list[str],
        local_strategy: TokenValidationStrategy,
        external_strategies: Optional[dict[str, TokenValidationStrategy]] = None,
    ) -> None:
        self._active_issuer = active_issuer
        self._trusted_issuers = set(trusted_issuers)
        self._strategies = {"local": local_strategy, **(external_strategies or {})}

    def validate(self, token: str, token_type: str = "access") -> TokenValidationResult:
        strategy = self._strategies.get(self._active_issuer)
        if strategy is None:
            logger.error("Unsupported active auth issuer", active_issuer=self._active_issuer)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unsupported authentication issuer strategy",
            )

        result = strategy.validate(token, token_type=token_type)
        if self._trusted_issuers and result.issuer not in self._trusted_issuers:
            logger.warning(
                "Token issuer is not trusted",
                issuer=result.issuer,
                trusted=sorted(self._trusted_issuers),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Untrusted token issuer",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return result
