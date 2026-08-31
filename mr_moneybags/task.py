from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class Task:
    raw_input: str
    id: str = field(default_factory=lambda: str(uuid4()), init=False)
    goal: str = field(init=False)
    expected_outcome: str | None = None
    constraints: list[str] | None = None
    acceptance_criteria: list[str] | None = None
    status: str = field(default="NEW", init=False)

    def __post_init__(self) -> None:
        self.goal = self.raw_input.strip()
        if not self.goal:
            raise ValueError("Task input must not be blank.")
