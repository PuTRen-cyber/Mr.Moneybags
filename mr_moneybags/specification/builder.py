from dataclasses import asdict, replace
import json
from uuid import NAMESPACE_URL, uuid5

from mr_moneybags.conversation.models import AlignmentResult, AlignmentState
from mr_moneybags.specification.models import IntentSpecification, SpecificationDecision, SpecificationStatus
from mr_moneybags.specification.readiness import evaluate_readiness


def build_intent_specification(alignment: AlignmentResult,
                               previous: IntentSpecification | None = None) -> IntentSpecification:
    current = alignment.current_intent
    version = previous.version + 1 if previous else 1
    supersedes = previous.id if previous else None
    confirmation = tuple(current.confirmation_turn_ids) if current.status == AlignmentState.CONFIRMED else ()
    claims = tuple(item for item in (
        current.goal, current.expected_outcome, *current.scope_in, *current.scope_out,
        *current.behavior_requirements, *current.constraints, *current.preferences,
    ) if item is not None)
    sources = tuple(dict.fromkeys((
        *current.source_turn_ids, *confirmation,
        *(source for claim in (*claims, *current.future_considerations) for source in claim.source_turn_ids),
        *(source for item in alignment.ambiguities for source in item.source_turn_ids),
        *(source for item in alignment.assumptions for source in item.source_turn_ids),
    )))
    identity = json.dumps({'alignment': asdict(alignment), 'version': version, 'supersedes': supersedes},
                          sort_keys=True, ensure_ascii=False)
    spec = IntentSpecification(
        id=str(uuid5(NAMESPACE_URL, identity)), version=version, goal=current.goal,
        source_intent_version=current.revision, expected_outcome=current.expected_outcome,
        scope_in=tuple(current.scope_in), scope_out=tuple(current.scope_out),
        behavior_requirements=tuple(current.behavior_requirements), constraints=tuple(current.constraints),
        preferences=tuple(current.preferences), future_considerations=tuple(current.future_considerations),
        user_decisions=tuple(SpecificationDecision(item, confirmation) for item in claims),
        working_assumptions=tuple(alignment.assumptions), source_turn_ids=sources,
        confirmation_turn_ids=confirmation, ambiguities=tuple(alignment.ambiguities),
        required_questions=tuple(alignment.questions_required), supersedes=supersedes,
    )
    readiness = evaluate_readiness(spec)
    return replace(spec, status=SpecificationStatus.READY if readiness.ready else SpecificationStatus.BLOCKED,
                   blocking_issues=readiness.blocking_reasons,
                   open_non_blocking_questions=readiness.non_blocking_unknowns)


def supersede_specification(old: IntentSpecification, new: IntentSpecification) -> IntentSpecification:
    if new.supersedes != old.id or new.version != old.version + 1:
        raise ValueError('The replacement must be the next version of this specification.')
    return replace(old, status=SpecificationStatus.SUPERSEDED, superseded_by=new.id)
