from dataclasses import dataclass

from mr_moneybags.conversation.models import (
    DecisionOwner, EvidenceReference, ImplementationDelegation, IntentKind, Materiality,
)


@dataclass(frozen=True)
class SemanticClaim:
    id: str
    concept_id: str
    kind: IntentKind
    value: str
    evidence: tuple[EvidenceReference, ...]
    protected_target: str | None = None
    implementation_delegation: ImplementationDelegation | None = None


@dataclass(frozen=True)
class SemanticAmbiguity:
    topic: str
    description: str
    evidence: tuple[EvidenceReference, ...]
    decision_owner: DecisionOwner
    materiality: Materiality
    candidate_interpretations: tuple[str, ...] = ()


@dataclass(frozen=True)
class SemanticResult:
    source_turn_id: str | None
    claims: tuple[SemanticClaim, ...]
    ambiguities: tuple[SemanticAmbiguity, ...] = ()
