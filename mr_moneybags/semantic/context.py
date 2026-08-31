from dataclasses import dataclass, field

from mr_moneybags.conversation.models import ConversationTurn, CurrentIntent, Role
from mr_moneybags.semantic.failures import ContextFailure


@dataclass(frozen=True)
class ProjectFact:
    value: str
    source: str
    trust_level: str = field(default='Project context / advisory', init=False)


@dataclass(frozen=True)
class IntentSummary:
    goal: str | None
    constraints: tuple[str, ...]
    current_scope: tuple[str, ...]
    scope_out: tuple[str, ...]
    future_considerations: tuple[str, ...]
    unresolved_choices: tuple[str, ...]
    trust_level: str = field(default='Derived Intent / advisory, not user evidence', init=False)


@dataclass(frozen=True)
class SemanticContext:
    current_turn: ConversationTurn
    recent_turns: tuple[ConversationTurn, ...]
    intent_summary: IntentSummary | None
    project_facts: tuple[ProjectFact, ...]


def build_semantic_context(
    turns: tuple[ConversationTurn, ...], current_intent: CurrentIntent | None = None,
    project_facts: tuple[ProjectFact, ...] = (),
) -> SemanticContext:
    latest = next((index for index in range(len(turns) - 1, -1, -1) if turns[index].role == Role.USER), None)
    if latest is None:
        raise ContextFailure('missing_user_turn')
    current = turns[latest]
    recent = turns[max(0, latest - 4):latest]
    if len(current.raw_text) > 8000 or any(len(t.raw_text) > 4000 for t in recent):
        raise ContextFailure('turn_exceeds_context_limit')
    summary = None
    if current_intent is not None:
        def values(items):
            return tuple(item.value[:240] for item in items[:8])
        summary = IntentSummary(
            current_intent.goal.value[:240] if current_intent.goal else None,
            values(current_intent.constraints),
            values(current_intent.scope_in + current_intent.behavior_requirements),
            values(current_intent.scope_out), values(current_intent.future_considerations),
            tuple(question.reason[:240] for question in current_intent.open_questions[:8]),
        )
    facts = tuple(ProjectFact(fact.value[:512], fact.source[:240]) for fact in project_facts[:8])
    return SemanticContext(current, recent, summary, facts)
