from dataclasses import dataclass
from enum import StrEnum


class SafetyStatus(StrEnum):
    ALLOW = 'ALLOW'
    REQUIRE_CONFIRMATION = 'REQUIRE_CONFIRMATION'
    BLOCK = 'BLOCK'


class RiskLevel(StrEnum):
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'


@dataclass(frozen=True)
class SafetyDecision:
    status: SafetyStatus
    risk_level: RiskLevel
    reasons: list[str]
    matched_rules: list[str]
