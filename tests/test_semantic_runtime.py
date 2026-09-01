from dataclasses import replace
from io import StringIO
import json
import unittest
from unittest.mock import patch

from mr_moneybags.cli import main
from mr_moneybags.conversation.models import IntentKind, ImplementationDelegation, ProjectConversation
from mr_moneybags.semantic.default import DeterministicInterpreter
from mr_moneybags.semantic.models import SemanticResult
from mr_moneybags.semantic.interpreter import interpret_conversation, SemanticValidationError
from test_semantic import claim


class RuntimeTest(unittest.TestCase):
    def run_cli(self, text, interpreter=None):
        output, error = StringIO(), StringIO()
        with patch.dict('os.environ', {'MR_MONEYBAGS_SEMANTIC_MODE': 'deterministic'}), \
                patch('builtins.input', return_value=text), patch('sys.stdout', output), patch('sys.stderr', error):
            status = main(interpreter=interpreter, debug=True)
        return status, output.getvalue(), error.getvalue()

    def test_default_cli_calls_semantic_interpreter_and_validation(self):
        original = DeterministicInterpreter.interpret
        with patch.object(DeterministicInterpreter, 'interpret', autospec=True, side_effect=original) as called, \
                patch('mr_moneybags.conversation.alignment.analyze_conversation', side_effect=AssertionError('Legacy bypass')):
            status, output, error = self.run_cli('Refactor the internal helper without changing behavior.')
        self.assertEqual(status, 0, error)
        called.assert_called_once()
        self.assertTrue(json.loads(output.split('Planning:\n')[1])['success'])

    def test_default_result_cannot_bypass_validation(self):
        with patch.object(DeterministicInterpreter, 'interpret', return_value=SemanticResult('stale', ())):
            status, output, error = self.run_cli('Keep my raw request.')
        self.assertEqual(status, 1)
        self.assertIn('stale_source_turn', error)
        self.assertNotIn('Planning:\n', output)
        failure = json.loads(output.split('Interpretation Failure:\n')[1])
        self.assertFalse(failure['success'])
        self.assertEqual(failure['conversation']['turns'][0]['raw_text'], 'Keep my raw request.')

    def test_injected_semantics_reach_all_downstream_layers(self):
        class Interpreter:
            def interpret(self, turns):
                turn = turns[-1]
                return SemanticResult(turn.id, (
                    claim(turn, IntentKind.GOAL, 'Add assignment management.', '管理作业', 'assignment'),
                    claim(turn, IntentKind.SCOPE_IN, 'Teachers create assignments.', '老师创建', 'create'),
                    claim(turn, IntentKind.FUTURE_CONSIDERATION, 'Grading', '评分以后做', 'grading'),
                    claim(turn, IntentKind.CONSTRAINT, 'Do not modify authentication logic.', '认证不变', 'auth', protected_target='authentication logic'),
                    claim(turn, IntentKind.CONSTRAINT, 'Ordinary implementation is delegated within scope.', '实现你们定', 'delegation',
                          implementation_delegation=ImplementationDelegation.ORDINARY_IMPLEMENTATION),
                ))
        status, output, error = self.run_cli('管理作业，老师创建；评分以后做；认证不变；实现你们定。', Interpreter())
        self.assertEqual(status, 0, error)
        alignment = json.loads(output.split('Conversation / Intent Alignment:\n')[1].split('Intent Specification / Readiness:\n')[0])['alignment']
        specification = json.loads(output.split('Intent Specification / Readiness:\n')[1].split('Planning:\n')[0])['specification']
        plan = json.loads(output.split('Planning:\n')[1])
        self.assertEqual(alignment['current_intent']['goal']['value'], 'Add assignment management.')
        self.assertEqual(specification['status'], 'READY')
        self.assertEqual(plan['mode'], 'ROLLING')
        self.assertNotIn('Grading', json.dumps(plan['current_work_unit']['scope_in']))
        self.assertNotIn('Grading', json.dumps(plan['current_work_unit']['acceptance_criteria']))
        statements = [d['statement'] for d in plan['agent_task_package']['user_decisions']]
        self.assertTrue(any(s.get('protected_target') == 'authentication logic' for s in statements))
        self.assertTrue(any(s.get('implementation_delegation') for s in statements))

    def test_invalid_evidence_fails_closed_through_cli(self):
        class Interpreter:
            def interpret(self, turns):
                item = claim(turns[-1], IntentKind.GOAL, 'Add a parser.', 'parser', 'parser')
                item = replace(item, evidence=(replace(item.evidence[0], quote='fabricated'),))
                return SemanticResult(turns[-1].id, (item,))
        status, output, error = self.run_cli('Add a parser.', Interpreter())
        self.assertEqual(status, 1)
        self.assertIn('quote_mismatch', error)
        self.assertNotIn('Intent Specification / Readiness:', output)

    def test_interpreter_exception_is_visible_without_internal_details(self):
        class Interpreter:
            def interpret(self, turns):
                raise RuntimeError('private provider details')
        status, output, error = self.run_cli('Add a parser.', Interpreter())
        self.assertEqual(status, 1)
        self.assertIn('interpreter_failed', error)
        self.assertNotIn('private provider details', output + error)
        self.assertNotIn('Planning:\n', output)

    def test_default_current_future_pipeline(self):
        status, output, error = self.run_cli('Add assignments. Include teacher creation. Later consider grading.')
        self.assertEqual(status, 0, error)
        plan = json.loads(output.split('Planning:\n')[1])
        self.assertEqual(plan['mode'], 'ROLLING')
        self.assertFalse(any('grading' in item['value'] for item in plan['current_work_unit']['acceptance_criteria']))

    def test_default_does_not_silently_drop_multiple_user_turns(self):
        conversation = ProjectConversation()
        conversation.add_turn('user', 'Add a parser.')
        conversation.add_turn('user', 'Do not modify authentication.')
        with self.assertRaisesRegex(SemanticValidationError, 'requires_single_user_turn'):
            interpret_conversation(conversation)
        self.assertEqual(len(conversation.turns), 2)

    def test_empty_default_interpretation_does_not_invent_goal(self):
        self.assertIsNone(interpret_conversation(ProjectConversation()).current_intent.goal)
