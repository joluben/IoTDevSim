"""
Prompt Guard — Anti Prompt-Injection (Security Layer 3)
Detects and logs prompt injection attempts in user messages.
Aligned with OWASP Top 10 for LLM Applications 2026.
"""

import re
import structlog
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple

logger = structlog.get_logger()

MAX_MESSAGE_LENGTH = 2000


class ThreatLevel(str, Enum):
    """Classification of detected threat severity."""
    NONE = "none"
    LOW = "low"        # Suspicious but likely false positive
    MEDIUM = "medium"  # Probable injection attempt
    HIGH = "high"      # Clear injection attempt
    CRITICAL = "critical"  # Aggressive override / jailbreak


@dataclass
class ScanResult:
    """Result of a prompt injection scan."""
    is_safe: bool
    threat_level: ThreatLevel
    matched_patterns: List[str]
    message: str  # Safe response message if blocked


# --- Pattern definitions ---

# HIGH: Direct instruction override / jailbreak attempts
_HIGH_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|rules|prompts)", re.I), "instruction_override"),
    (re.compile(r"(disregard|forget)\s+(all\s+)?(previous|prior|your)\s+(instructions|rules|context)", re.I), "instruction_override"),
    (re.compile(r"you\s+are\s+now\s+(a|an|my)\s+", re.I), "role_override"),
    (re.compile(r"(enter|switch\s+to|activate)\s+(admin|root|sudo|god|debug|developer)\s*(mode)?", re.I), "privilege_escalation"),
    (re.compile(r"(reveal|show|print|output|display)\s+(your|the|system)\s+(prompt|instructions|rules|config)", re.I), "prompt_extraction"),
    (re.compile(r"jailbreak", re.I), "jailbreak"),
    (re.compile(r"DAN\s*mode|do\s+anything\s+now", re.I), "jailbreak"),
    (re.compile(r"pretend\s+(you('re|\s+are)\s+)?(a|an|not)\s+(AI|assistant|bound|restricted)", re.I), "role_override"),
    (re.compile(r"(new|override|replace)\s+(system\s+)?(role|persona|identity|instructions)", re.I), "instruction_override"),
]

# MEDIUM: Suspicious delimiters and framing attempts
_MEDIUM_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"^system\s*:", re.I | re.M), "system_prompt_injection"),
    (re.compile(r"^(assistant|human|user)\s*:", re.I | re.M), "role_injection"),
    (re.compile(r"<<<\s*.*\s*>>>", re.S), "delimiter_injection"),
    (re.compile(r"---\s*(system|instructions|rules)\s*---", re.I), "delimiter_injection"),
    (re.compile(r"###\s*(system|instructions|override)\s*###", re.I), "delimiter_injection"),
    (re.compile(r"\[INST\]|\[/INST\]|\[SYS\]|\[/SYS\]", re.I), "template_injection"),
    (re.compile(r"<\|?(system|im_start|im_end|endoftext)\|?>", re.I), "template_injection"),
    (re.compile(r"(execute|run)\s+(this\s+)?(code|command|script|query|sql)", re.I), "code_execution"),
    (re.compile(r"access\s+(other|another)\s+user", re.I), "cross_user_access"),
    (re.compile(r"(show|list|dump)\s+(all\s+)?(users|accounts|passwords|credentials|tokens|secrets)", re.I), "data_exfiltration"),
]

# LOW: Mildly suspicious but often legitimate
_LOW_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"(override|bypass)\s+security", re.I), "security_bypass"),
    (re.compile(r"(raw|direct)\s+(database|db|sql|api)\s+(access|query)", re.I), "direct_access"),
    (re.compile(r"(export|download)\s+all\s+(data|records|users)", re.I), "bulk_export"),
]

SAFE_REJECTION = (
    "No puedo procesar esa solicitud. ¿Puedo ayudarte con algo relacionado "
    "con tus conexiones, dispositivos, datasets o proyectos de simulación?"
)


def scan_message(message: str) -> ScanResult:
    """
    Scan a user message for prompt injection patterns.

    Returns a ScanResult with threat classification.
    Messages exceeding MAX_MESSAGE_LENGTH are blocked.
    """
    # Length check
    if len(message) > MAX_MESSAGE_LENGTH:
        logger.warning(
            "prompt_guard.message_too_long",
            length=len(message),
            max_length=MAX_MESSAGE_LENGTH,
        )
        return ScanResult(
            is_safe=False,
            threat_level=ThreatLevel.MEDIUM,
            matched_patterns=["message_too_long"],
            message=f"El mensaje excede el límite de {MAX_MESSAGE_LENGTH} caracteres. Por favor, acórtalo.",
        )

    matched: List[str] = []
    max_level = ThreatLevel.NONE

    # Check HIGH patterns
    for pattern, label in _HIGH_PATTERNS:
        if pattern.search(message):
            matched.append(label)
            max_level = ThreatLevel.HIGH

    # Check MEDIUM patterns (only if not already HIGH)
    if max_level != ThreatLevel.HIGH:
        for pattern, label in _MEDIUM_PATTERNS:
            if pattern.search(message):
                matched.append(label)
                if max_level.value < ThreatLevel.MEDIUM.value:
                    max_level = ThreatLevel.MEDIUM

    # Check LOW patterns
    if max_level == ThreatLevel.NONE:
        for pattern, label in _LOW_PATTERNS:
            if pattern.search(message):
                matched.append(label)
                max_level = ThreatLevel.LOW

    # Multiple MEDIUM matches escalate to HIGH
    medium_count = sum(1 for p, _ in _MEDIUM_PATTERNS if p.search(message))
    if medium_count >= 2 and max_level == ThreatLevel.MEDIUM:
        max_level = ThreatLevel.HIGH

    # Determine if safe
    is_safe = max_level in (ThreatLevel.NONE, ThreatLevel.LOW)

    if matched:
        logger.warning(
            "prompt_guard.patterns_detected",
            threat_level=max_level.value,
            patterns=matched,
            blocked=not is_safe,
        )

    return ScanResult(
        is_safe=is_safe,
        threat_level=max_level,
        matched_patterns=matched,
        message="" if is_safe else SAFE_REJECTION,
    )
