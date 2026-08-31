from dataclasses import dataclass
from enum import StrEnum

from mr_moneybags.conversation.models import Assumption
from mr_moneybags.specification.models import SpecificationDecision


class PlanningMode(StrEnum):
    FAST_PATH = 'FAST_PATH'
    ROLLING = 'ROLLING'


class StageStatus(StrEnum):
    CURRENT = 'CURRENT'
    FUTURE = 'FUTURE'
    SUPERSEDED = 'SUPERSEDED'


class PackageStatus(StrEnum):
    DRAFT = 'DRAFT'
    READY_FOR_DELEGATION = 'READY_FOR_DELEGATION'
    SUPERSEDED = 'SUPERSEDED'


class PlanStatus(StrEnum):
    PREPARED = 'PREPARED'
    SUPERSEDED = 'SUPERSEDED'


@dataclass(frozen=True)
class PlanningClaim:
    value: str
    source_ids: tuple[str, ...]
    basis: str


@dataclass(frozen=True)
class ContextSource:
    path: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class ContextSummary:
    claims: tuple[PlanningClaim, ...]
    sources: tuple[ContextSource, ...]
    warnings: tuple[str, ...]
    trust_level: str = 'Derived Context / Interpretation'


@dataclass(frozen=True)
class PlanStage:
    id: str
    title: str
    objective: PlanningClaim
    status: StageStatus
    scope_summary: tuple[PlanningClaim, ...]
    why_this_stage: PlanningClaim
    source_ids: tuple[str, ...]
    committed: bool


@dataclass(frozen=True)
class PlanningHorizon:
    id: str
    version: int
    goal: PlanningClaim
    mode: PlanningMode
    current_stage: PlanStage
    future_stages: tuple[PlanStage, ...]
    source_specification_id: str
    source_specification_version: int
    source_context_sources: tuple[str, ...]
    status: PlanStatus = PlanStatus.PREPARED
    supersedes: str | None = None
    superseded_by: str | None = None


@dataclass(frozen=True)
class CurrentWorkUnit:
    id: str
    version: int
    objective: PlanningClaim
    why_now: PlanningClaim
    scope_in: tuple[PlanningClaim, ...]
    scope_out: tuple[PlanningClaim, ...]
    constraints: tuple[PlanningClaim, ...]
    behavior_requirements: tuple[PlanningClaim, ...]
    acceptance_criteria: tuple[PlanningClaim, ...]
    verification_expectations: tuple[PlanningClaim, ...]
    allowed_agent_discretion: tuple[PlanningClaim, ...]
    known_assumptions: tuple[Assumption, ...]
    source_specification_id: str
    source_specification_version: int
    source_stage_id: str
    source_ids: tuple[str, ...]
    status: PlanStatus = PlanStatus.PREPARED
    supersedes: str | None = None
    superseded_by: str | None = None


@dataclass(frozen=True)
class AgentTaskPackage:
    id: str
    version: int
    task_title: str
    objective: PlanningClaim
    why: PlanningClaim
    project_context_summary: ContextSummary
    scope_in: tuple[PlanningClaim, ...]
    scope_out: tuple[PlanningClaim, ...]
    constraints: tuple[PlanningClaim, ...]
    behavior_requirements: tuple[PlanningClaim, ...]
    acceptance_criteria: tuple[PlanningClaim, ...]
    verification_expectations: tuple[PlanningClaim, ...]
    working_assumptions: tuple[Assumption, ...]
    user_decisions: tuple[SpecificationDecision, ...]
    allowed_agent_discretion: tuple[PlanningClaim, ...]
    source_specification_id: str
    source_specification_version: int
    source_stage_id: str
    source_work_unit_id: str
    provenance: tuple[str, ...]
    status: PackageStatus = PackageStatus.READY_FOR_DELEGATION
    supersedes: str | None = None
    superseded_by: str | None = None


@dataclass(frozen=True)
class StageBriefing:
    stage_title: str
    objective: str
    why_now: str
    in_scope: tuple[str, ...]
    out_of_scope: tuple[str, ...]
    done_when: tuple[str, ...]


@dataclass(frozen=True)
class PlanningFailure:
    code: str
    reason: str
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class PlanningResult:
    success: bool
    source_specification_id: str
    mode: PlanningMode | None = None
    planning_horizon: PlanningHorizon | None = None
    current_work_unit: CurrentWorkUnit | None = None
    agent_task_package: AgentTaskPackage | None = None
    stage_briefing: StageBriefing | None = None
    blocking_reasons: tuple[PlanningFailure, ...] = ()
    warnings: tuple[str, ...] = ()
