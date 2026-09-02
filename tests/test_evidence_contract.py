from dataclasses import asdict, replace
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
        data = asdict(self.result)
        for claim in data['claims']:
            for evidence in claim['evidence']:
                evidence.pop('quote')
        return SemanticModelResponse(json.dumps(data, ensure_ascii=False))


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
        required = ('do not generate', 'only turn_id, start, and end', 'quote = raw_text[start:end]',
                    'exclusive', 'omit the unsupported claim', 'rather than guess offsets')
        for phrase in required:
            self.assertIn(phrase, INSTRUCTIONS.lower())
        self.assertIn('Valid:', INSTRUCTIONS)
        self.assertIn('Invalid:', INSTRUCTIONS)
        self.assertIn('semantic value', INSTRUCTIONS.lower())
        self.assertIn('quote is not model input', INSTRUCTIONS)

    def test_prompt_makes_singleton_contract_explicit(self):
        required = ('single highest-level objective', 'at most one goal', 'single overall result',
                    'at most one expected_outcome', 'must not become multiple goals',
                    'one goal plus multiple constraints', 'keep one higher-level goal')
        for phrase in required:
            self.assertIn(phrase, INSTRUCTIONS.lower())

    def test_runtime_diagnostic_identifies_mismatch_without_provider_dump(self):
        raw = '保持空格  和标点。'
        class RuntimeClient:
            calls = 0

            def interpret(self, request):
                self.calls += 1
                turn = request.context.current_turn
                result = asdict(semantic_result(turn, turn.raw_text, value='Preserve formatting.',
                                                start=0, end=len(turn.raw_text) + 1))
                result['claims'][0]['evidence'][0].pop('quote')
                return SemanticModelResponse(json.dumps(result, ensure_ascii=False))
        client = RuntimeClient()
        output, error = StringIO(), StringIO()
        with patch('builtins.input', return_value=raw), patch('sys.stdout', output), patch('sys.stderr', error):
            status = main(interpreter=ModelBackedSemanticInterpreter(client), debug=True)
        self.assertEqual(status, 1)
        failure = json.loads(output.getvalue().split('Interpretation Failure:\n')[1])
        self.assertEqual(failure['category'], 'EvidenceValidationFailure')
        self.assertEqual(failure['diagnostic']['semantic_field'], 'claims[0].evidence[0]')
        self.assertEqual(failure['diagnostic']['turn_id'], failure['conversation']['turns'][0]['id'])
        self.assertEqual(failure['code'], 'invalid_span_bounds')
        self.assertEqual(failure['diagnostic']['quote'], '')
        self.assertIsNone(failure['diagnostic']['source_span'])
        self.assertEqual(client.calls, 1)
        self.assertNotIn('provider_response', failure)
        self.assertNotIn('instructions', failure)
        self.assertNotIn('reasoning', failure)
        self.assertNotIn('Planning:', output.getvalue())

    def test_chinese_reproduction_valid_spans_materialize_exact_source_text(self):
        raw = '课程管理系统增加作业功能。老师可以创建作业，学生可以查看。提交和评分以后再考虑。'
        conv = conversation(raw)
        turn = conv.turns[0]
        goal = replace(semantic_result(turn, '课程管理系统增加作业功能', value='Manage assignments.').claims[0],
                       id='goal', concept_id='assignment')
        future = replace(semantic_result(turn, '提交和评分以后再考虑', value='Submission and grading are future scope.',
                                         kind=IntentKind.FUTURE_CONSIDERATION).claims[0], id='future',
                         concept_id='submission')
        result = SemanticResult(turn.id, (goal, future))
        alignment = interpret_conversation(conv, ModelBackedSemanticInterpreter(Client(result)))
        for statement in alignment.statements:
            evidence = statement.evidence[0]
            self.assertEqual(evidence.quote, raw[evidence.start:evidence.end])

    def test_chinese_reproduction_out_of_bounds_span_is_not_materialized(self):
        raw = '课程管理系统增加作业功能。老师可以创建作业，学生可以查看。提交和评分以后再考虑。'

        class RuntimeClient:
            def interpret(self, request):
                turn = request.context.current_turn
                result = semantic_result(turn, '后再考虑。', value='Future consideration.', start=35, end=42)
                data = asdict(result)
                for claim in data['claims']:
                    for evidence in claim['evidence']:
                        evidence.pop('quote')
                return SemanticModelResponse(json.dumps(data, ensure_ascii=False))

        output, error = StringIO(), StringIO()
        with patch('builtins.input', return_value=raw), patch('sys.stdout', output), patch('sys.stderr', error):
            status = main(interpreter=ModelBackedSemanticInterpreter(RuntimeClient()))
        self.assertEqual(status, 1)
        failure = json.loads(output.getvalue().split('Interpretation Failure:\n')[1])
        self.assertEqual(failure['category'], 'EvidenceValidationFailure')
        self.assertEqual(failure['code'], 'invalid_span_bounds')
        self.assertEqual(failure['diagnostic']['start'], 35)
        self.assertEqual(failure['diagnostic']['end'], 42)
        self.assertEqual(failure['diagnostic']['quote'], '')
        self.assertIsNone(failure['diagnostic']['source_span'])

    def test_model_path_rejects_invalid_span_without_fallback(self):
        conv = conversation('不要改变当前颜色。')
        result = semantic_result(conv.turns[0], conv.turns[0].raw_text, start=-1, end=len(conv.turns[0].raw_text))
        client = Client(result)
        with patch('mr_moneybags.semantic.default.DeterministicInterpreter.interpret',
                   side_effect=AssertionError('fallback')) as fallback:
            with self.assertRaises(EvidenceValidationFailure):
                interpret_conversation(conv, ModelBackedSemanticInterpreter(client))
        self.assertEqual(client.calls, 1)
        fallback.assert_not_called()
