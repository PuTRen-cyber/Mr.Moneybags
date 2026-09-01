from dataclasses import dataclass


@dataclass(frozen=True)
class HumanReport:
    summary: str
    scope_in: list[str]
    scope_out: list[str]
    risk: str
    status: str


@dataclass(frozen=True)
class CodexBrief:
    task_title: str
    objective: str
    requirements: list[str]
    constraints: list[str]
    acceptance_criteria: list[str]
    implementation_guidance: list[str]
    verification: list[str]
    risk_notes: list[str]
