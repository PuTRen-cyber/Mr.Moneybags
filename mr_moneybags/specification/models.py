from dataclasses import dataclass, field
from enum import StrEnum

from mr_moneybags.conversation.models import Ambiguity, Assumption, IntentStatement, QuestionRequest


class SpecificationStatus(StrEnum):
    DRAFT = 'DRAFT'
    BLOCKED = 'BLOCKED'
    READY = 'READY'
    SUPERSEDED = 'SUPERSEDED'


class ReadinessStatus(StrEnum):
    READY = 'READY'
    NOT_READY = 'NOT_READY'


class BlockingCategory(StrEnum):
    UNRESOLVED_MATERIAL_AMBIGUITY = 'UNRESOLVED_MATERIAL_AMBIGUITY'
    MISSING_REQUIRED_CONFIRMATION = 'MISSING_REQUIRED_CONFIRMATION'
    CONFLICTING_USER_INTENT = 'CONFLICTING_USER_INTENT'
    HIGH_IMPACT_UNRESOLVED_DECISION = 'HIGH_IMPACT_UNRESOLVED_DECISION'
    INSUFFICIENT_GOAL = 'INSUFFICIENT_GOAL'
    UNRESOLVED_SCOPE = 'UNRESOLVED_SCOPE'


@dataclass(frozen=True)
class BlockingReason:
    category: BlockingCategory
    description: str
    source_turn_ids: tuple[str, ...] = ()
    source_statement_ids: tuple[str, ...] = ()
    ambiguity_id: str | None = None
    assumption_id: str | None = None


@dataclass(frozen=True)
class SpecificationDecision:
    statement: IntentStatement
    confirmation_turn_ids: tuple[str, ...] = ()
    basis: str = field(default='Active user-derived intent; confirmation is recorded separately', init=False)


@dataclass(frozen=True)
class IntentSpecification:
    id: str
    version: int
    goal: IntentStatement | None
    source_intent_version: str | None
    expected_outcome: IntentStatement | None = None
    scope_in: tuple[IntentStatement, ...] = ()
    scope_out: tuple[IntentStatement, ...] = ()
    behavior_requirements: tuple[IntentStatement, ...] = ()
    constraints: tuple[IntentStatement, ...] = ()
    preferences: tuple[IntentStatement, ...] = ()
    future_considerations: tuple[IntentStatement, ...] = ()
    user_decisions: tuple[SpecificationDecision, ...] = ()
    working_assumptions: tuple[Assumption, ...] = ()
    open_non_blocking_questions: tuple[QuestionRequest, ...] = ()
    blocking_issues: tuple[BlockingReason, ...] = ()
    source_turn_ids: tuple[str, ...] = ()
    confirmation_turn_ids: tuple[str, ...] = ()
    ambiguities: tuple[Ambiguity, ...] = ()
    required_questions: tuple[QuestionRequest, ...] = ()
    status: SpecificationStatus = SpecificationStatus.DRAFT
    supersedes: str | None = None
    superseded_by: str | None = None
    trust_level: str = field(default='Derived Intent Specification / Interpretation', init=False)


@dataclass(frozen=True)
class ReadinessResult:
    ready: bool
    status: ReadinessStatus
    blocking_reasons: tuple[BlockingReason, ...]
    non_blocking_unknowns: tuple[QuestionRequest, ...]
    assumptions_in_effect: tuple[Assumption, ...]
    source_intent_version: str | None
    specification_id: str
