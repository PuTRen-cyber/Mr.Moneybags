from dataclasses import asdict
from io import StringIO
import json
import unittest
from unittest.mock import patch

from mr_moneybags.cli import main
from mr_moneybags.conversation.models import EvidenceReference, IntentKind, ProjectConversation
from mr_moneybags.semantic.failures import EvidenceValidationFailure
from mr_moneybags.semantic.interpreter import SemanticValidationError, interpret_conversation, validate_semantics
from mr_moneybags.semantic.model import ModelBackedSemanticInterpreter, SemanticModelResponse
from mr_moneybags.semantic.models import SemanticClaim, SemanticResult
from mr_moneybags.semantic.prompt import INSTRUCTIONS


class Client:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def interpret(self, request):
        self.calls += 1
        return SemanticModelResponse(json.dumps(asdict(self.result), ensure_ascii=False))


def conversation(text):
    value = ProjectConversation()
    value.add_turn('user', text)
    return value


def semantic_result(turn, quote, value='Normalized interpretation.', kind=IntentKind.GOAL,
                    start=None, end=None):
    actual_start = turn.raw_text.find(quote) if start is None else start
    actual_end = actual_start + len(quote) if end is None else end
    evidence = EvidenceReference(turn.id, actual_start, actual_end, quote)
    return SemanticResult(turn.id, (SemanticClaim('claim', 'concept', kind, value, (evidence,)),))


class EvidenceContractTest(unittest.TestCase):
    def assert_strict_rejection(self, raw, quote, start=0, end=None):
        conv = conversation(raw)
        result = semantic_result(conv.turns[0], quote, start=start, end=len(raw) if end is None else end)
        with self.assertRaisesRegex(SemanticValidationError, 'quote_mismatch'):
            validate_semantics(result, tuple(conv.turns))

    def test_exact_chinese_substring_and_normalized_value_pass(self):
        conv = conversation('请保留  原始格式，并继续处理。')
        quote = '保留  原始格式'
        result = semantic_result(conv.turns[0], quote, value='Preserve the original format.')
        validate_semantics(result, tuple(conv.turns))
        alignment = interpret_conversation(conv, ModelBackedSemanticInterpreter(Client(result)))
        self.assertEqual(alignment.current_intent.goal.value, 'Preserve the original format.')
        self.assertEqual(alignment.current_intent.goal.evidence[0].quote, quote)

    def test_paraphrased_chinese_quote_fails_without_fuzzy_matching(self):
        self.assert_strict_rejection('界面保持原样', '界面维持原样')

    def test_punctuation_modified_quote_fails(self):
        self.assert_strict_rejection('先支持新增、编辑。', '先支持新增，编辑。')

    def test_reordered_quote_fails(self):
        self.assert_strict_rejection('先完成查询和筛选', '先完成筛选和查询')

    def test_exact_future_scope_and_behavior_spans_pass(self):
        raw = '现在允许用户查看记录。归档功能稍后处理。'
        conv = conversation(raw)
        turn = conv.turns[0]
        behavior_quote = '允许用户查看记录'
        future_quote = '归档功能稍后处理'
        claims = (
            semantic_result(turn, behavior_quote, 'Users can view records.', IntentKind.BEHAVIOR_REQUIREMENT).claims[0],
            SemanticClaim('future', 'future', IntentKind.FUTURE_CONSIDERATION, 'Archiving is future scope.',
                (EvidenceReference(turn.id, raw.index(future_quote), raw.index(future_quote) + len(future_quote), future_quote),)),
        )
        validate_semantics(SemanticResult(turn.id, claims), tuple(conv.turns))

    def test_quote_and_offsets_must_agree(self):
        conv = conversation('前缀 精确片段 后缀')
        turn = conv.turns[0]
        quote = '精确片段'
        start = turn.raw_text.index(quote)
        validate_semantics(semantic_result(turn, quote, start=start, end=start + len(quote)), tuple(conv.turns))
        for wrong_start, wrong_end in ((start - 1, start + len(quote)), (start, start + len(quote) + 1)):
            with self.assertRaisesRegex(SemanticValidationError, 'quote_mismatch'):
                validate_semantics(semantic_result(turn, quote, start=wrong_start, end=wrong_end), tuple(conv.turns))

    def test_prompt_makes_verbatim_contract_explicit_with_examples(self):
        required = ('character-for-character', 'one contiguous substring', 'raw_text[start:end] == quote',
                    'exclusive', 'omit the unsupported claim', 'never synthesize')
        for phrase in required:
            self.assertIn(phrase, INSTRUCTIONS.lower())
        self.assertIn('Valid:', INSTRUCTIONS)
        self.assertIn('Invalid:', INSTRUCTIONS)
        self.assertIn('semantic value', INSTRUCTIONS)
        self.assertIn('evidence quote', INSTRUCTIONS)

    def test_runtime_diagnostic_identifies_mismatch_without_provider_dump(self):
        raw = '保持空格  和标点。'
        class RuntimeClient:
            calls = 0

            def interpret(self, request):
                self.calls += 1
                turn = request.context.current_turn
                result = semantic_result(turn, '保持空格 和标点。', value='Preserve formatting.',
                                         start=0, end=len(turn.raw_text))
                return SemanticModelResponse(json.dumps(asdict(result), ensure_ascii=False))
        client = RuntimeClient()
        output, error = StringIO(), StringIO()
        with patch('builtins.input', return_value=raw), patch('sys.stdout', output), patch('sys.stderr', error):
            status = main(interpreter=ModelBackedSemanticInterpreter(client))
        self.assertEqual(status, 1)
        failure = json.loads(output.getvalue().split('Interpretation Failure:\n')[1])
        self.assertEqual(failure['category'], 'EvidenceValidationFailure')
        self.assertEqual(failure['diagnostic']['semantic_field'], 'claims[0].evidence[0]')
        self.assertEqual(failure['diagnostic']['turn_id'], failure['conversation']['turns'][0]['id'])
        self.assertEqual(failure['diagnostic']['quote'], '保持空格 和标点。')
        self.assertEqual(failure['diagnostic']['source_span'], raw)
        self.assertEqual(client.calls, 1)
        self.assertNotIn('provider_response', failure)
        self.assertNotIn('instructions', failure)
        self.assertNotIn('reasoning', failure)
        self.assertNotIn('Planning:', output.getvalue())

    def test_model_path_rejects_paraphrase_without_fallback(self):
        conv = conversation('不要改变当前颜色。')
        result = semantic_result(conv.turns[0], '不要修改当前颜色。', start=0, end=len(conv.turns[0].raw_text))
        client = Client(result)
        with patch('mr_moneybags.semantic.default.DeterministicInterpreter.interpret',
                   side_effect=AssertionError('fallback')) as fallback:
            with self.assertRaises(EvidenceValidationFailure):
                interpret_conversation(conv, ModelBackedSemanticInterpreter(client))
        self.assertEqual(client.calls, 1)
        fallback.assert_not_called()
