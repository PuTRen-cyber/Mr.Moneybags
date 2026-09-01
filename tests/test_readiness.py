from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict
from io import StringIO
from unittest import TestCase
from unittest.mock import patch

from mr_moneybags.cli import main
from mr_moneybags.conversation.models import CurrentIntent, EvidenceReference, IntentKind, IntentStatement
from mr_moneybags.readiness import IntentReadinessClassifier, ReadinessStatus
from mr_moneybags.semantic.models import SemanticClaim, SemanticResult


def current_intent(text: str, *, open_questions=None) -> CurrentIntent:
    return CurrentIntent(
        goal=IntentStatement('goal', IntentKind.GOAL, text, ('turn',), 0.5),
        open_questions=list(open_questions or ()),
    )


class Interpreter:
    def interpret(self, turns):
        turn = turns[-1]
        evidence = EvidenceReference(turn.id, 0, len(turn.raw_text), turn.raw_text)
        return SemanticResult(turn.id, (
            SemanticClaim('goal', 'goal', IntentKind.GOAL, turn.raw_text, (evidence,)),
        ))


class IntentReadinessClassifierTest(TestCase):
    def setUp(self):
        self.classifier = IntentReadinessClassifier()

    def assert_status(self, text, status):
        result = self.classifier.classify(text, current_intent(text))
        self.assertEqual(result.status, status)
        self.assertTrue(result.reason)

    def test_readme_change_is_ready(self):
        self.assert_status('修改README增加开发启动说明', ReadinessStatus.READY)

    def test_detailed_feature_is_ready(self):
        self.assert_status(
            '给课程管理系统增加作业功能。老师可以创建作业，学生可以查看。提交和评分以后再考虑。',
            ReadinessStatus.READY,
        )

    def test_product_vision_requires_discovery(self):
        result = self.classifier.classify(
            '我想做一个AI帮助大学生学习的软件',
            current_intent('我想做一个AI帮助大学生学习的软件'),
        )
        self.assertEqual(result.status, ReadinessStatus.DISCOVERY_REQUIRED)
        self.assertIn('first version scope', result.missing_information)
        self.assertTrue(result.suggested_questions)

    def test_vague_improvement_needs_clarification(self):
        result = self.classifier.classify('优化登录体验', current_intent('优化登录体验'))
        self.assertEqual(result.status, ReadinessStatus.NEEDS_CLARIFICATION)
        self.assertIn('acceptance criteria', result.missing_information)
        self.assertTrue(result.suggested_questions)

    def test_non_ready_runtime_stops_before_planning_reporting_and_fallback(self):
        for text, expected in (
            ('我想做一个AI帮助大学生学习的软件', ReadinessStatus.DISCOVERY_REQUIRED),
            ('优化登录体验', ReadinessStatus.NEEDS_CLARIFICATION),
        ):
            stdout = StringIO()
            stderr = StringIO()
            with self.subTest(text=text), \
                    patch('builtins.input', return_value=text), \
                    patch('mr_moneybags.cli.Planner.plan') as plan, \
                    patch('mr_moneybags.cli.build_codex_brief') as brief, \
                    patch('mr_moneybags.semantic.default.DeterministicInterpreter.interpret') as fallback, \
                    redirect_stdout(stdout), redirect_stderr(stderr):
                status = main(interpreter=Interpreter())
            self.assertEqual(status, 0, stderr.getvalue())
            self.assertIn(f'"status": "{expected}"', stdout.getvalue())
            self.assertNotIn('Codex Brief:', stdout.getvalue())
            plan.assert_not_called()
            brief.assert_not_called()
            fallback.assert_not_called()

    def test_result_serializes_as_structured_output(self):
        result = self.classifier.classify('优化登录体验', current_intent('优化登录体验'))
        self.assertEqual(asdict(result)['status'], ReadinessStatus.NEEDS_CLARIFICATION)
