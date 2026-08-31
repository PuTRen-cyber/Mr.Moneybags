from mr_moneybags.conversation.extractor import IntentExtractor
from mr_moneybags.conversation.models import ConversationTurn, EvidenceReference, Role
from mr_moneybags.semantic.interpreter import SemanticValidationError
from mr_moneybags.semantic.models import SemanticClaim, SemanticResult


class DeterministicInterpreter:
    def interpret(self, turns: tuple[ConversationTurn, ...]) -> SemanticResult:
        users = [turn for turn in turns if turn.role == Role.USER]
        if not users:
            return SemanticResult(None, ())
        if len(users) != 1:
            raise SemanticValidationError('default_interpreter_requires_single_user_turn')
        turn = users[0]
        evidence = (EvidenceReference(turn.id, 0, len(turn.raw_text), turn.raw_text),)
        claims = tuple(SemanticClaim(item.id, item.id, item.kind, item.value, evidence)
                       for item in IntentExtractor().extract(turn))
        return SemanticResult(turn.id, claims)
