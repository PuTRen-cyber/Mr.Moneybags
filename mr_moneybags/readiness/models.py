from dataclasses import dataclass, field
from enum import StrEnum


class ReadinessStatus(StrEnum):
    READY = 'READY'
    NEEDS_CLARIFICATION = 'NEEDS_CLARIFICATION'
    DISCOVERY_REQUIRED = 'DISCOVERY_REQUIRED'


@dataclass(frozen=True)
class IntentReadinessResult:
    status: ReadinessStatus
    reason: str
    missing_information: list[str] = field(default_factory=list)
    suggested_questions: list[str] = field(default_factory=list)
