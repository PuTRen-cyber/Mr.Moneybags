from dataclasses import replace
import re

from mr_moneybags.conversation.ambiguity import AmbiguityDetector
from mr_moneybags.conversation.extractor import IntentExtractor, confirmation_signal
from mr_moneybags.conversation.models import (
    AlignmentResult, AlignmentState, Ambiguity, AmbiguityStatus, Assumption,
    AssumptionStatus, CurrentIntent, DecisionOwner, IntentKind, IntentStatement,
    Materiality, ProjectConversation, QuestionRequest, Role,
)


def _safe(assumption: Assumption | None) -> bool:
    return (assumption is not None and assumption.reversible
            and assumption.materiality == Materiality.LOW
            and assumption.status == AssumptionStatus.ACTIVE)


def requires_user_confirmation(ambiguity: Ambiguity) -> bool:
    if ambiguity.status in {AmbiguityStatus.RESOLVED, AmbiguityStatus.DEFERRED}:
        return False
    if ambiguity.materiality == Materiality.HIGH:
        return True
    if ambiguity.materiality == Materiality.LOW:
        return ambiguity.safe_assumption is not None and not ambiguity.safe_assumption.reversible
    if ambiguity.decision_owner == DecisionOwner.USER:
        return True
    if ambiguity.decision_owner == DecisionOwner.SHARED:
        return not _safe(ambiguity.safe_assumption)
    return (ambiguity.safe_assumption is not None
            and (not ambiguity.safe_assumption.reversible or ambiguity.safe_assumption.materiality == Materiality.HIGH))


def _active(statements: list[IntentStatement]) -> list[IntentStatement]:
    superseded = {identifier for item in statements for identifier in item.supersedes}
    return [item for item in statements if item.id not in superseded]


def _current(statements: list[IntentStatement], revision: str) -> CurrentIntent:
    active = _active(statements)
    by_kind = {kind: [item for item in active if item.kind == kind] for kind in IntentKind}
    return CurrentIntent(
        goal=by_kind[IntentKind.GOAL][-1] if by_kind[IntentKind.GOAL] else None,
        expected_outcome=by_kind[IntentKind.EXPECTED_OUTCOME][-1] if by_kind[IntentKind.EXPECTED_OUTCOME] else None,
        constraints=by_kind[IntentKind.CONSTRAINT], preferences=by_kind[IntentKind.PREFERENCE],
        scope_in=by_kind[IntentKind.SCOPE_IN], scope_out=by_kind[IntentKind.SCOPE_OUT],
        behavior_requirements=by_kind[IntentKind.BEHAVIOR_REQUIREMENT],
        future_considerations=by_kind[IntentKind.FUTURE_CONSIDERATION],
        source_turn_ids=list(dict.fromkeys(source for item in active for source in item.source_turn_ids)),
        revision=revision,
    )


def _questions(ambiguities: list[Ambiguity]) -> list[QuestionRequest]:
    return [QuestionRequest(item.topic, item.description, item.id, item.materiality)
            for item in ambiguities if requires_user_confirmation(item)]


def analyze_conversation(conversation: ProjectConversation) -> AlignmentResult:
    extractor = IntentExtractor()
    detector = AmbiguityDetector()
    statements = []
    ambiguities = []
    assumptions = []
    changes = []
    current = CurrentIntent()
    pending = None
    for turn in conversation.turns:
        if turn.role == Role.JIA:
            pending = turn.confirmation_for if turn.confirmation_for == current.revision else None
            continue
        signal = confirmation_signal(turn.raw_text)
        if signal:
            if pending is None or pending != current.revision or current.goal is None:
                continue
            if signal == "positive":
                ambiguities = [replace(item, status=AmbiguityStatus.RESOLVED,
                                       resolution="Explicitly acknowledged by the user.",
                                       source_turn_ids=(*item.source_turn_ids, turn.id))
                               if item.topic in {"destructive_action", "intent_change", "confirmation_unclear"} else item
                               for item in ambiguities]
                changes = [item for item in ambiguities if item.topic == "intent_change"]
                if not _questions(ambiguities):
                    current.status = AlignmentState.CONFIRMED
                    current.confirmation_turn_ids = [turn.id]
                    assumptions = [replace(item, status=AssumptionStatus.CONFIRMED,
                                           source_turn_ids=(*item.source_turn_ids, turn.id)) for item in assumptions]
                    confirmed = {item.id: item for item in assumptions}
                    ambiguities = [replace(item, safe_assumption=confirmed[item.safe_assumption.id],
                                           status=AmbiguityStatus.RESOLVED,
                                           source_turn_ids=(*item.source_turn_ids, turn.id))
                                   if item.safe_assumption and item.safe_assumption.id in confirmed else item
                                   for item in ambiguities]
                else:
                    current.status = AlignmentState.ALIGNING
            else:
                current.status = AlignmentState.ALIGNING
                current.confirmation_turn_ids = []
                assumptions = [replace(item, status=AssumptionStatus.REJECTED,
                                       source_turn_ids=(*item.source_turn_ids, turn.id)) for item in assumptions]
                rejected = {item.id: item for item in assumptions}
                ambiguities = [replace(item, safe_assumption=rejected[item.safe_assumption.id],
                                       status=AmbiguityStatus.OPEN, resolution=None)
                               if item.safe_assumption and item.safe_assumption.id in rejected else item
                               for item in ambiguities]
                ambiguities.append(Ambiguity(
                    f"{turn.id}:confirmation_rejected", "confirmation_rejected",
                    "The proposed understanding was rejected; revised intent is needed.", (),
                    tuple((*current.source_turn_ids, turn.id)), DecisionOwner.USER, Materiality.MEDIUM,
                ))
            pending = None
            continue
        extracted = extractor.extract(turn)
        if pending is not None and (not extracted or all(item.confidence < 0.8 for item in extracted)):
            current.status = AlignmentState.ALIGNING
            current.confirmation_turn_ids = []
            pending = None
            ambiguities.append(Ambiguity(
                f"{turn.id}:confirmation_unclear", "confirmation_unclear",
                "The response is not a controlled confirmation; a fresh review is required.", (),
                tuple((*current.source_turn_ids, turn.id)), DecisionOwner.USER, Materiality.MEDIUM,
            ))
            continue
        if not extracted:
            continue
        pending = None
        correction = bool(re.match(r"\s*(?:actually\b|更正|改为)", turn.raw_text, re.IGNORECASE))
        for item in extracted:
            old = [previous for previous in _active(statements) if previous.kind == item.kind]
            if old and (item.kind in {IntentKind.GOAL, IntentKind.EXPECTED_OUTCOME} or correction):
                item = replace(item, supersedes=tuple(previous.id for previous in old))
                if item.value != old[-1].value:
                    changes.append(Ambiguity(
                        f"{item.id}:intent_change", "intent_change",
                        "The new interpretation supersedes an earlier one; confirm the revised direction.",
                        (old[-1].value, item.value), tuple(dict.fromkeys((*old[-1].source_turn_ids, *item.source_turn_ids))),
                        DecisionOwner.USER, Materiality.MEDIUM,
                    ))
            statements.append(item)
        current = _current(statements, turn.id)
        ambiguities = detector.detect(_active(statements)) + changes
        assumptions = []
        for index, item in enumerate(ambiguities):
            if not requires_user_confirmation(item) and _safe(item.safe_assumption):
                assumptions.append(item.safe_assumption)
                ambiguities[index] = replace(item, status=AmbiguityStatus.ASSUMED, resolution=item.safe_assumption.value)
        current.status = AlignmentState.ALIGNING if _questions(ambiguities) else AlignmentState.DRAFT
    questions = _questions(ambiguities)
    current.assumptions = assumptions
    current.open_questions = questions
    return AlignmentResult(current, statements, ambiguities, assumptions, questions, current.status)
