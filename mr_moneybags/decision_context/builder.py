from mr_moneybags.conversation.alignment import requires_user_confirmation
from mr_moneybags.conversation.models import AlignmentResult, AmbiguityStatus, DecisionOwner
from mr_moneybags.decision_context.models import DecisionContext


def _unique(items):
    seen = set()
    unique = []
    for item in items:
        if item.id not in seen:
            seen.add(item.id)
            unique.append(item)
    return tuple(unique)


def _same_evidence(left, right):
    return {(item.turn_id, item.start, item.end) for item in left.evidence} == {
        (item.turn_id, item.start, item.end) for item in right.evidence
    }


def build_decision_context(alignment: AlignmentResult) -> DecisionContext:
    current = alignment.current_intent
    deferred = (*current.scope_out, *current.future_considerations)
    scope_in = tuple(item for item in (*current.scope_in, *current.behavior_requirements)
                     if not any(_same_evidence(item, excluded) for excluded in deferred))
    active = tuple(item for item in (
        current.goal, current.expected_outcome, *scope_in, *current.scope_out,
        *current.constraints, *current.preferences,
    ) if item is not None)
    scope_out = deferred
    question_ids = {item.ambiguity_id for item in current.open_questions}
    open_decisions = tuple(item for item in alignment.ambiguities
                           if item.id in question_ids and item.status == AmbiguityStatus.OPEN
                           and item.decision_owner == DecisionOwner.USER
                           and requires_user_confirmation(item))
    return DecisionContext(
        objective=current.goal,
        scope_in=_unique(scope_in),
        scope_out=_unique(scope_out),
        confirmed_information=_unique(active),
        open_user_decisions=open_decisions,
        agent_proposals=(),
    )
