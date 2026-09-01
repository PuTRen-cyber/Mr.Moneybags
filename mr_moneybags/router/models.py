from dataclasses import dataclass
from enum import StrEnum


class TaskMode(StrEnum):
    FAST_PATH = 'FAST_PATH'
    STANDARD_PATH = 'STANDARD_PATH'
    DISCOVERY_PATH = 'DISCOVERY_PATH'


@dataclass(frozen=True)
class RouterDecision:
    mode: TaskMode
    reason: str
    next_action: str
