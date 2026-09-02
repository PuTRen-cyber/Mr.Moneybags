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


def build_decision_context(alignment: AlignmentResult) -> DecisionContext:
    current = alignment.current_intent
    active = tuple(item for item in (
        current.goal, current.expected_outcome, *current.scope_in, *current.scope_out,
        *current.behavior_requirements, *current.constraints, *current.preferences,
    ) if item is not None)
    scope_out = (*current.scope_out, *current.future_considerations)
    question_ids = {item.ambiguity_id for item in current.open_questions}
    open_decisions = tuple(item for item in alignment.ambiguities
                           if item.id in question_ids and item.status == AmbiguityStatus.OPEN
                           and item.decision_owner == DecisionOwner.USER
                           and requires_user_confirmation(item))
    return DecisionContext(
        objective=current.goal,
        scope_in=tuple(current.scope_in),
        scope_out=_unique(scope_out),
        confirmed_information=_unique(active),
        open_user_decisions=open_decisions,
        agent_proposals=(),
    )
