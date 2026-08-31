from dataclasses import asdict, replace
import json
from typing import Protocol
from uuid import NAMESPACE_URL, uuid5

from mr_moneybags.conversation.alignment import requires_user_confirmation
from mr_moneybags.conversation.ambiguity import AmbiguityDetector
from mr_moneybags.conversation.models import (
    AlignmentResult, AlignmentState, Ambiguity, AmbiguityStatus, AssumptionStatus,
    ConversationTurn, CurrentIntent, DecisionOwner, EvidenceReference,
    ImplementationDelegation, IntentKind, IntentStatement, Materiality,
    ProjectConversation, QuestionRequest, Role,
)
from mr_moneybags.semantic.models import SemanticAmbiguity, SemanticClaim, SemanticResult


class SemanticInterpreter(Protocol):
    def interpret(self, turns: tuple[ConversationTurn, ...]) -> SemanticResult: ...


class SemanticValidationError(ValueError):
    pass


def validate_semantics(result: SemanticResult, turns: tuple[ConversationTurn, ...]) -> None:
    def require(condition, code):
        if not condition:
            raise SemanticValidationError(code)

    require(isinstance(result, SemanticResult), 'invalid_result_type')
    users = [turn for turn in turns if turn.role == Role.USER]
    require(result.source_turn_id == (users[-1].id if users else None), 'stale_source_turn')
    require(isinstance(result.claims, tuple) and len(result.claims) <= 64, 'invalid_claim_collection')
    require(isinstance(result.ambiguities, tuple) and len(result.ambiguities) <= 32, 'invalid_ambiguity_collection')
    by_id = {turn.id: turn for turn in users}

    def text(value):
        return isinstance(value, str) and bool(value.strip())

    def evidence(references):
        require(isinstance(references, tuple) and 0 < len(references) <= 8, 'missing_or_invalid_evidence')
        for ref in references:
            require(isinstance(ref, EvidenceReference), 'invalid_evidence_type')
            require(isinstance(ref.turn_id, str) and ref.turn_id in by_id, 'non_user_evidence')
            turn = by_id[ref.turn_id]
            require(type(ref.start) is int and type(ref.end) is int, 'invalid_span_type')
            require(0 <= ref.start < ref.end <= len(turn.raw_text), 'invalid_span_bounds')
            require(text(ref.quote) and turn.raw_text[ref.start:ref.end] == ref.quote, 'quote_mismatch')

    identifiers = set()
    concepts = {}
    counts = {}
    for item in result.claims:
        require(isinstance(item, SemanticClaim), 'invalid_claim_type')
        require(text(item.id) and item.id not in identifiers, 'duplicate_or_empty_claim_id')
        identifiers.add(item.id)
        require(text(item.concept_id) and text(item.value), 'empty_claim')
        require(isinstance(item.kind, IntentKind), 'invalid_claim_kind')
        evidence(item.evidence)
        require(item.protected_target is None or (text(item.protected_target) and item.kind in {
            IntentKind.CONSTRAINT, IntentKind.SCOPE_OUT}), 'invalid_protected_boundary')
        require(item.implementation_delegation is None or (
            item.implementation_delegation == ImplementationDelegation.ORDINARY_IMPLEMENTATION
            and item.kind == IntentKind.CONSTRAINT), 'invalid_delegation')
        concepts.setdefault(item.concept_id, set()).add(item.kind)
        counts[item.kind] = counts.get(item.kind, 0) + 1
    for kind in (IntentKind.GOAL, IntentKind.EXPECTED_OUTCOME):
        require(counts.get(kind, 0) <= 1, 'multiple_singleton_claims')
    for kinds in concepts.values():
        require(not (IntentKind.FUTURE_CONSIDERATION in kinds and kinds.intersection({
            IntentKind.GOAL, IntentKind.EXPECTED_OUTCOME, IntentKind.SCOPE_IN,
            IntentKind.BEHAVIOR_REQUIREMENT})), 'current_future_conflict')
    for item in result.ambiguities:
        require(isinstance(item, SemanticAmbiguity), 'invalid_ambiguity_type')
        require(text(item.topic) and text(item.description), 'empty_ambiguity')
        require(isinstance(item.decision_owner, DecisionOwner) and isinstance(item.materiality, Materiality),
                'invalid_ambiguity_classification')
        require(isinstance(item.candidate_interpretations, tuple) and all(text(v) for v in item.candidate_interpretations),
                'invalid_candidates')
        evidence(item.evidence)


def interpret_conversation(conversation: ProjectConversation, interpreter: SemanticInterpreter) -> AlignmentResult:
    turns = tuple(conversation.turns)
    result = interpreter.interpret(turns)
    validate_semantics(result, turns)
    revision = str(uuid5(NAMESPACE_URL, json.dumps(asdict(result), sort_keys=True, ensure_ascii=False)))
    statements = [IntentStatement(
        id=f'{revision}:{item.id}', kind=item.kind, value=item.value,
        source_turn_ids=tuple(dict.fromkeys(ref.turn_id for ref in item.evidence)), confidence=0.5,
        evidence=item.evidence, protected_target=item.protected_target,
        implementation_delegation=item.implementation_delegation,
    ) for item in result.claims]
    grouped = {kind: [item for item in statements if item.kind == kind] for kind in IntentKind}
    ambiguities = AmbiguityDetector().detect(statements)
    ambiguities.extend(Ambiguity(
        f'{revision}:semantic:{index}', item.topic, item.description, item.candidate_interpretations,
        tuple(dict.fromkeys(ref.turn_id for ref in item.evidence)), item.decision_owner, item.materiality,
        evidence=item.evidence,
    ) for index, item in enumerate(result.ambiguities))
    assumptions = []
    for index, item in enumerate(ambiguities):
        assumption = item.safe_assumption
        if (not requires_user_confirmation(item) and assumption is not None
                and assumption.materiality == Materiality.LOW and assumption.reversible
                and assumption.status == AssumptionStatus.ACTIVE):
            assumptions.append(assumption)
            ambiguities[index] = replace(item, status=AmbiguityStatus.ASSUMED, resolution=assumption.value)
    questions = [QuestionRequest(item.topic, item.description, item.id, item.materiality)
                 for item in ambiguities if requires_user_confirmation(item)]
    state = AlignmentState.ALIGNING if questions else AlignmentState.DRAFT
    current = CurrentIntent(
        goal=next(iter(grouped[IntentKind.GOAL]), None),
        expected_outcome=next(iter(grouped[IntentKind.EXPECTED_OUTCOME]), None),
        constraints=grouped[IntentKind.CONSTRAINT], preferences=grouped[IntentKind.PREFERENCE],
        scope_in=grouped[IntentKind.SCOPE_IN], scope_out=grouped[IntentKind.SCOPE_OUT],
        behavior_requirements=grouped[IntentKind.BEHAVIOR_REQUIREMENT],
        future_considerations=grouped[IntentKind.FUTURE_CONSIDERATION],
        assumptions=assumptions, open_questions=questions,
        source_turn_ids=list(dict.fromkeys(source for item in statements for source in item.source_turn_ids)),
        revision=revision, status=state,
    )
    return AlignmentResult(current, statements, ambiguities, assumptions, questions, state)
