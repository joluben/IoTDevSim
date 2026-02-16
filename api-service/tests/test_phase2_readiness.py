from fastapi import HTTPException
import pytest

from app.core.security import create_access_token, verify_token
from app.core.simple_config import settings
from app.core.token_validator import IssuerAwareTokenValidator, LocalJWTValidationStrategy


def test_verify_token_uses_local_strategy_successfully():
    token = create_access_token(subject="phase2-test-user")

    subject = verify_token(token, token_type="access")

    assert subject == "phase2-test-user"


def test_issuer_aware_validator_rejects_untrusted_issuer_claim():
    validator = IssuerAwareTokenValidator(
        active_issuer="local",
        trusted_issuers=["iotdevsim-local"],
        local_strategy=LocalJWTValidationStrategy(
            secret_key=settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
            issuer=settings.AUTH_LOCAL_ISSUER,
        ),
    )

    token = create_access_token(
        subject="phase2-test-user",
        additional_claims={"iss": "malicious-issuer"},
    )

    with pytest.raises(HTTPException) as exc_info:
        validator.validate(token, token_type="access")

    assert exc_info.value.status_code == 401
    assert "issuer" in str(exc_info.value.detail).lower()


def test_issuer_aware_validator_fails_for_unsupported_active_strategy():
    validator = IssuerAwareTokenValidator(
        active_issuer="keycloak",
        trusted_issuers=["local", "keycloak"],
        local_strategy=LocalJWTValidationStrategy(
            secret_key=settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
            issuer=settings.AUTH_LOCAL_ISSUER,
        ),
    )

    token = create_access_token(subject="phase2-test-user")

    with pytest.raises(HTTPException) as exc_info:
        validator.validate(token, token_type="access")

    assert exc_info.value.status_code == 500
