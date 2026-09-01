from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from unittest import TestCase
from unittest.mock import patch

from mr_moneybags.cli import main
from mr_moneybags.conversation.models import EvidenceReference, IntentKind
from mr_moneybags.router import DecisionRouter, TaskMode
from mr_moneybags.semantic.models import SemanticClaim, SemanticResult


class Interpreter:
    def interpret(self, turns):
        turn = turns[-1]
        evidence = EvidenceReference(turn.id, 0, len(turn.raw_text), turn.raw_text)
        return SemanticResult(turn.id, (
            SemanticClaim('goal', 'goal', IntentKind.GOAL, turn.raw_text, (evidence,)),
        ))


class DecisionRouterTest(TestCase):
    def setUp(self):
        self.router = DecisionRouter()

    def test_readme_change_uses_fast_path(self):
        decision = self.router.classify('README增加Quick Start')
        self.assertEqual(decision.mode, TaskMode.FAST_PATH)
        self.assertEqual(decision.next_action, 'create_codex_brief')

    def test_feature_request_uses_standard_path(self):
        decision = self.router.classify('课程管理系统增加作业功能。老师可以创建作业，学生可以查看。')
        self.assertEqual(decision.mode, TaskMode.STANDARD_PATH)
        self.assertEqual(decision.next_action, 'create_codex_brief')

    def test_product_vision_uses_discovery_path(self):
        decision = self.router.classify('我想做一个AI帮助大学生学习的软件。')
        self.assertEqual(decision.mode, TaskMode.DISCOVERY_PATH)
        self.assertEqual(decision.next_action, 'ask_clarifying_questions')

    def test_vague_existing_system_improvement_uses_standard_path(self):
        decision = self.router.classify('优化登录体验。')
        self.assertEqual(decision.mode, TaskMode.STANDARD_PATH)

    def test_discovery_runtime_stops_before_planning_and_codex_brief(self):
        stdout = StringIO()
        stderr = StringIO()
        with patch('builtins.input', return_value='我想做一个AI帮助大学生学习的软件。'), \
                patch('mr_moneybags.cli.Planner.plan') as plan, \
                patch('mr_moneybags.cli.build_codex_brief') as brief, \
                redirect_stdout(stdout), redirect_stderr(stderr):
            status = main(interpreter=Interpreter())
        self.assertEqual(status, 0, stderr.getvalue())
        self.assertIn('Intent Router:', stdout.getvalue())
        self.assertIn('"mode": "DISCOVERY_PATH"', stdout.getvalue())
        self.assertNotIn('Codex Brief:', stdout.getvalue())
        plan.assert_not_called()
        brief.assert_not_called()
