from dataclasses import dataclass

from mr_moneybags.conversation.models import Ambiguity, IntentStatement


@dataclass(frozen=True)
class DecisionContext:
    objective: IntentStatement | None
    scope_in: tuple[IntentStatement, ...] = ()
    scope_out: tuple[IntentStatement, ...] = ()
    confirmed_information: tuple[IntentStatement, ...] = ()
    open_user_decisions: tuple[Ambiguity, ...] = ()
    agent_proposals: tuple[IntentStatement, ...] = ()
    stage: str | None = None
