from dataclasses import dataclass
from typing import Protocol

from mr_moneybags.conversation.models import ConversationTurn, CurrentIntent, IntentKind
from mr_moneybags.semantic.context import SemanticContext, ProjectFact, build_semantic_context
from mr_moneybags.semantic.failures import EvidenceValidationFailure, ModelOutputFailure, TransportFailure
from mr_moneybags.semantic.interpreter import SemanticValidationError, validate_semantics
from mr_moneybags.semantic.models import SemanticResult
from mr_moneybags.semantic.schema import decode_result


@dataclass(frozen=True)
class SemanticModelRequest:
    context: SemanticContext


@dataclass(frozen=True)
class SemanticModelResponse:
    json_text: str


class SemanticModelClient(Protocol):
    def interpret(self, request: SemanticModelRequest) -> SemanticModelResponse: ...


class ModelBackedSemanticInterpreter:
    def __init__(self, client: SemanticModelClient, *, current_intent: CurrentIntent | None = None,
                 project_facts: tuple[ProjectFact, ...] = ()):
        self.client = client
        self.current_intent = current_intent
        self.project_facts = project_facts

    def interpret(self, turns: tuple[ConversationTurn, ...]) -> SemanticResult:
        context = build_semantic_context(turns, self.current_intent, self.project_facts)
        try:
            response = self.client.interpret(SemanticModelRequest(context))
        except (TransportFailure, ModelOutputFailure):
            raise
        except Exception:
            raise TransportFailure('model_client_failed') from None
        if not isinstance(response, SemanticModelResponse):
            raise ModelOutputFailure('invalid_response_type')
        result = decode_result(response.json_text)
        try:
            validate_semantics(result, context.recent_turns + (context.current_turn,))
        except SemanticValidationError as error:
            if str(error) in {'stale_source_turn', 'missing_or_invalid_evidence', 'invalid_evidence_type',
                              'non_user_evidence', 'invalid_span_type', 'invalid_span_bounds', 'quote_mismatch'}:
                raise EvidenceValidationFailure(str(error)) from None
            raise ModelOutputFailure(str(error)) from None
        if not any(item.kind == IntentKind.GOAL for item in result.claims) and not result.ambiguities:
            raise ModelOutputFailure('missing_goal_or_material_question')
        return result
