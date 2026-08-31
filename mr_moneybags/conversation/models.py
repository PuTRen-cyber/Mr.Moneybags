from dataclasses import dataclass, field
from enum import StrEnum
from uuid import uuid4


class Role(StrEnum):
    USER = "user"
    JIA = "jia"


class DecisionOwner(StrEnum):
    USER = "user"
    JIA_AGENT = "jia_agent"
    SHARED = "shared"


class Materiality(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AlignmentState(StrEnum):
    DRAFT = "DRAFT"
    ALIGNING = "ALIGNING"
    CONFIRMED = "CONFIRMED"


class AmbiguityStatus(StrEnum):
    OPEN = "OPEN"
    ASSUMED = "ASSUMED"
    RESOLVED = "RESOLVED"
    DEFERRED = "DEFERRED"


class AssumptionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class IntentKind(StrEnum):
    GOAL = "goal"
    EXPECTED_OUTCOME = "expected_outcome"
    CONSTRAINT = "constraint"
    PREFERENCE = "preference"
    SCOPE_IN = "scope_in"
    SCOPE_OUT = "scope_out"
    BEHAVIOR_REQUIREMENT = "behavior_requirement"
    FUTURE_CONSIDERATION = "future_consideration"


@dataclass(frozen=True)
class ConversationTurn:
    id: str
    role: Role
    raw_text: str
    sequence: int
    confirmation_for: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", Role(self.role))
        if self.confirmation_for is not None and self.role != Role.JIA:
            raise ValueError("Only JIA turns may request confirmation.")


@dataclass(frozen=True)
class EvidenceReference:
    turn_id: str
    start: int
    end: int
    quote: str


class ImplementationDelegation(StrEnum):
    ORDINARY_IMPLEMENTATION = 'ordinary_implementation_within_scope_and_constraints'


@dataclass(frozen=True)
class IntentStatement:
    id: str
    kind: IntentKind
    value: str
    source_turn_ids: tuple[str, ...]
    confidence: float
    status: str = "CANDIDATE"
    supersedes: tuple[str, ...] = ()
    trust_level: str = field(default="Derived Intent / Interpretation", init=False)
    evidence: tuple[EvidenceReference, ...] = ()
    protected_target: str | None = None
    implementation_delegation: ImplementationDelegation | None = None


@dataclass(frozen=True)
class Assumption:
    id: str
    value: str
    reason: str
    source_turn_ids: tuple[str, ...]
    materiality: Materiality
    reversible: bool
    status: AssumptionStatus = AssumptionStatus.ACTIVE


@dataclass(frozen=True)
class Ambiguity:
    id: str
    topic: str
    description: str
    candidate_interpretations: tuple[str, ...]
    source_turn_ids: tuple[str, ...]
    decision_owner: DecisionOwner
    materiality: Materiality
    resolution: str | None = None
    status: AmbiguityStatus = AmbiguityStatus.OPEN
    safe_assumption: Assumption | None = None
    context_sources: tuple[str, ...] = ()
    evidence: tuple[EvidenceReference, ...] = ()


@dataclass(frozen=True)
class QuestionRequest:
    topic: str
    reason: str
    ambiguity_id: str
    priority: Materiality


@dataclass
class CurrentIntent:
    goal: IntentStatement | None = None
    expected_outcome: IntentStatement | None = None
    constraints: list[IntentStatement] = field(default_factory=list)
    preferences: list[IntentStatement] = field(default_factory=list)
    scope_in: list[IntentStatement] = field(default_factory=list)
    scope_out: list[IntentStatement] = field(default_factory=list)
    behavior_requirements: list[IntentStatement] = field(default_factory=list)
    future_considerations: list[IntentStatement] = field(default_factory=list)
    assumptions: list[Assumption] = field(default_factory=list)
    open_questions: list[QuestionRequest] = field(default_factory=list)
    source_turn_ids: list[str] = field(default_factory=list)
    confirmation_turn_ids: list[str] = field(default_factory=list)
    revision: str | None = None
    status: AlignmentState = AlignmentState.DRAFT
    trust_level: str = field(default="Derived Intent / Interpretation", init=False)


@dataclass
class AlignmentResult:
    current_intent: CurrentIntent
    statements: list[IntentStatement]
    ambiguities: list[Ambiguity]
    assumptions: list[Assumption]
    questions_required: list[QuestionRequest]
    alignment_state: AlignmentState
    trust_level: str = field(default="Derived Intent / Interpretation", init=False)


@dataclass
class ProjectConversation:
    id: str = field(default_factory=lambda: str(uuid4()))
    turns: list[ConversationTurn] = field(default_factory=list)
    evidence_type: str = field(default="Raw conversation evidence; roles identify the speaker", init=False)

    def add_turn(self, role: Role | str, raw_text: str,
                 confirmation_for: str | None = None) -> ConversationTurn:
        turn = ConversationTurn(str(uuid4()), Role(role), raw_text, len(self.turns) + 1, confirmation_for)
        self.turns.append(turn)
        return turn

    def request_confirmation(self, intent: CurrentIntent) -> ConversationTurn:
        if intent.revision is None or intent.goal is None:
            raise ValueError("A current intent must exist before requesting confirmation.")
        return self.add_turn(Role.JIA, "Confirm the displayed current intent.", intent.revision)
