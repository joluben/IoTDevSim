"""
Output Filter — Sensitive Data Sanitization (Security Layer 4)
Regex-based filtering applied to every SSE chunk before sending to the client.
Prevents accidental leakage of credentials, keys, tokens, and PII.
"""

import re
import structlog
from typing import List, Tuple

logger = structlog.get_logger()

# Replacement placeholder
_REDACTED = "[REDACTED]"

# --- Sensitive data patterns ---
_PATTERNS: List[Tuple[re.Pattern, str, str]] = [
    # JWT tokens
    (
        re.compile(r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}"),
        _REDACTED,
        "jwt_token",
    ),
    # API keys (OpenAI sk-, Anthropic sk-ant-, generic api_key/api-key patterns)
    (
        re.compile(r"(sk-|pk-|sk-ant-|api[_-]?key[\"'\s:=]+)[a-zA-Z0-9]{20,}"),
        _REDACTED,
        "api_key",
    ),
    # Private keys (PEM)
    (
        re.compile(r"-----BEGIN\s+(RSA\s+|EC\s+|DSA\s+|ENCRYPTED\s+)?PRIVATE\s+KEY-----[\s\S]*?-----END\s+(RSA\s+|EC\s+|DSA\s+|ENCRYPTED\s+)?PRIVATE\s+KEY-----"),
        _REDACTED,
        "private_key",
    ),
    # Certificates (PEM)
    (
        re.compile(r"-----BEGIN\s+CERTIFICATE-----[\s\S]*?-----END\s+CERTIFICATE-----"),
        _REDACTED,
        "certificate",
    ),
    # Password patterns in key=value or JSON style
    (
        re.compile(r'(password|passwd|pwd|secret|token)[\s"\']*[:=]\s*[\s"\']*\S{8,}', re.I),
        r"\1: " + _REDACTED,
        "password_value",
    ),
    # Connection strings with embedded credentials
    (
        re.compile(r"(mongodb|postgres|mysql|redis|amqp|mqtt)://[^\s\"']+:[^\s\"']+@", re.I),
        r"\1://***:***@",
        "connection_string",
    ),
    # Email addresses (PII)
    (
        re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"),
        _REDACTED,
        "email",
    ),
    # AWS-style access keys
    (
        re.compile(r"(AKIA|ABIA|ACCA|ASIA)[A-Z0-9]{16}"),
        _REDACTED,
        "aws_key",
    ),
    # Generic hex/base64 secrets that look like keys (32+ chars of hex)
    (
        re.compile(r'(secret|key|token|salt)[\s"\']*[:=]\s*[\s"\']*[a-fA-F0-9]{32,}', re.I),
        r"\1: " + _REDACTED,
        "hex_secret",
    ),
]


def filter_output(text: str) -> str:
    """
    Sanitize a text chunk by replacing detected sensitive data.

    Returns the filtered text. Logs each filter activation for audit
    without recording the actual sensitive content.
    """
    if not text:
        return text

    filtered = text
    activated: List[str] = []

    for pattern, replacement, label in _PATTERNS:
        if pattern.search(filtered):
            filtered = pattern.sub(replacement, filtered)
            activated.append(label)

    if activated:
        logger.warning(
            "output_filter.activated",
            patterns=activated,
            original_length=len(text),
            filtered_length=len(filtered),
        )

    return filtered
