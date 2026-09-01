from dataclasses import asdict, replace
from io import StringIO
import json
import unittest
from unittest.mock import Mock, patch

from mr_moneybags.cli import main
from mr_moneybags.context.models import ProjectContext
from mr_moneybags.conversation.models import IntentKind, ImplementationDelegation
from mr_moneybags.semantic.context import build_semantic_context, ProjectFact
from mr_moneybags.semantic.model import ModelBackedSemanticInterpreter, SemanticModelResponse
from mr_moneybags.semantic.failures import (
    ContextFailure, EvidenceValidationFailure, ModelOutputFailure, TransportFailure,
)
from mr_moneybags.semantic.interpreter import interpret_conversation
from mr_moneybags.semantic.models import SemanticResult
from mr_moneybags.specification.builder import build_intent_specification
from mr_moneybags.planning.planner import Planner
from test_semantic import conversation, claim


class Client:
    def __init__(self, produce):
        self.produce = produce
        self.requests = []

    def interpret(self, request):
        self.requests.append(request)
        return SemanticModelResponse(json.dumps(self.produce(request.context), ensure_ascii=False))


def span_payload(value):
    data = json.loads(json.dumps(value, ensure_ascii=False))
    def visit(item):
        if isinstance(item, dict):
            if set(item) >= {'turn_id', 'start', 'end', 'quote'}:
                item.pop('quote')
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)
    visit(data)
    return data


def result(context, *items):
    return span_payload(asdict(SemanticResult(context.current_turn.id, tuple(items))))


def goal(context):
    turn = context.current_turn
    return result(context, claim(turn, IntentKind.GOAL, turn.raw_text, turn.raw_text, 'goal'))


class ContextTest(unittest.TestCase):
    def test_current_is_exact_and_recent_window_is_bounded(self):
        conv = conversation('oldest')
        for index in range(8):
            conv.add_turn('jia' if index % 2 else 'user', str(index))
        conv.add_turn('user', '  当前原文 😀  ')
        context = build_semantic_context(tuple(conv.turns))
        self.assertEqual(context.current_turn.raw_text, '  当前原文 😀  ')
        self.assertEqual(context.current_turn.id, conv.turns[-1].id)
        self.assertEqual([t.id for t in context.recent_turns], [t.id for t in conv.turns[-5:-1]])
        self.assertEqual(context.project_facts, ())
        self.assertNotIn('oldest', json.dumps(asdict(context)))

    def test_summary_and_project_facts_are_compact_and_distinct(self):
        conv = conversation('Add search.')
        alignment = interpret_conversation(conv)
        alignment.current_intent.constraints = [replace(alignment.current_intent.goal, value='x' * 1000)] * 20
        facts = tuple(ProjectFact('y' * 1000, 'README.md') for _ in range(20))
        context = build_semantic_context(tuple(conv.turns), alignment.current_intent, facts)
        self.assertEqual(len(context.intent_summary.constraints), 8)
        self.assertLessEqual(len(context.intent_summary.constraints[0]), 240)
        self.assertEqual(len(context.project_facts), 8)
        self.assertLessEqual(len(context.project_facts[0].value), 512)
        self.assertIn('Derived', context.intent_summary.trust_level)
        self.assertNotIn('user', context.project_facts[0].trust_level.lower())
        self.assertNotIn('sources', asdict(context))
        self.assertNotIn('confirmation_turn_ids', asdict(context.intent_summary))

    def test_oversize_current_or_recent_turn_fails_before_call(self):
        for current, previous in [('x' * 8001, 'old'), ('new', 'x' * 4001)]:
            with self.subTest(current_length=len(current)):
                conv = conversation(previous)
                conv.add_turn('user', current)
                client = Client(goal)
                with self.assertRaises(ContextFailure):
                    interpret_conversation(conv, ModelBackedSemanticInterpreter(client))
                self.assertEqual(client.requests, [])

    def test_no_user_turn_fails_before_model_call(self):
        client = Client(goal)
        with self.assertRaisesRegex(ContextFailure, 'missing_user_turn'):
            ModelBackedSemanticInterpreter(client).interpret(())
        self.assertEqual(client.requests, [])


class ModelRuntimeTest(unittest.TestCase):
    def run_cli(self, text, client):
        output, errors = StringIO(), StringIO()
        with patch('builtins.input', return_value=text), patch('sys.stdout', output), patch('sys.stderr', errors):
            status = main(interpreter=ModelBackedSemanticInterpreter(client))
        return status, output.getvalue(), errors.getvalue()

    def test_protected_constraints_and_paraphrases_reach_package(self):
        for text, boundary, target in (
            ('把 README 安装说明整理清楚，不修改项目代码。', '不修改项目代码', 'project code'),
            ('完善安装指引，源代码保持原样。', '源代码保持原样', 'project code'),
            ('把登录页面做得更现代一点，但认证逻辑不要动。', '认证逻辑不要动', 'authentication logic'),
            ('更新登录界面的视觉呈现，保持原来的身份验证机制。', '保持原来的身份验证机制', 'authentication logic'),
        ):
            def produce(context):
                turn = context.current_turn
                return result(context,
                    claim(turn, IntentKind.GOAL, text.split('，')[0], text.split('，')[0], 'goal'),
                    claim(turn, IntentKind.CONSTRAINT, 'Preserve ' + target, boundary, 'protect', protected_target=target))
            with self.subTest(text=text):
                client = Client(produce)
                status, output, errors = self.run_cli(text, client)
                self.assertEqual(status, 0, errors)
                plan = json.loads(output.split('Planning:\n')[1])
                self.assertTrue(plan['success'])
                self.assertTrue(any(d['statement'].get('protected_target') == target
                                    for d in plan['agent_task_package']['user_decisions']))
                self.assertEqual(len(client.requests), 1)
                self.assertEqual(client.requests[0].context.project_facts, ())

    def test_explicit_delegation_and_paraphrase_reach_package(self):
        for text, delegation in (
            ('给这个工具增加搜索，具体怎么实现你们决定。', '具体怎么实现你们决定'),
            ('需要检索功能，内部实现方案由开发者选择。', '内部实现方案由开发者选择'),
        ):
            def produce(context):
                turn = context.current_turn
                return result(context,
                    claim(turn, IntentKind.GOAL, 'Add search.', text.split('，')[0], 'search'),
                    claim(turn, IntentKind.CONSTRAINT, 'Delegate ordinary implementation.', delegation, 'delegate',
                          implementation_delegation=ImplementationDelegation.ORDINARY_IMPLEMENTATION))
            status, output, errors = self.run_cli(text, Client(produce))
            self.assertEqual(status, 0, errors)
            plan = json.loads(output.split('Planning:\n')[1])
            self.assertTrue(any(d['statement'].get('implementation_delegation') == ImplementationDelegation.ORDINARY_IMPLEMENTATION
                                for d in plan['agent_task_package']['user_decisions']))
            self.assertNotIn('CONFIRMED', output)

    def test_current_future_behavior_reaches_rolling_without_leak(self):
        for text, current, future in (
            ('给课程管理系统增加作业功能。老师可以创建作业，学生可以查看。提交和评分以后再考虑。',
             '老师可以创建作业，学生可以查看', '提交和评分以后再考虑'),
            ('先做教师布置和学生浏览作业；交作业及打分留到后续。', '教师布置和学生浏览作业', '交作业及打分留到后续'),
        ):
            def produce(context):
                turn = context.current_turn
                return result(context,
                    claim(turn, IntentKind.GOAL, 'Manage assignments.', current, 'assignment'),
                    claim(turn, IntentKind.BEHAVIOR_REQUIREMENT, 'Teachers create; students view.', current, 'current'),
                    claim(turn, IntentKind.FUTURE_CONSIDERATION, 'Submission and grading.', future, 'future'))
            status, output, errors = self.run_cli(text, Client(produce))
            self.assertEqual(status, 0, errors)
            plan = json.loads(output.split('Planning:\n')[1])
            self.assertEqual(plan['mode'], 'ROLLING')
            self.assertIn('Teachers create', json.dumps(plan['current_work_unit']))
            self.assertNotIn('Submission', json.dumps(plan['current_work_unit']['scope_in']))
            self.assertNotIn('Submission', json.dumps(plan['current_work_unit']['acceptance_criteria']))
            self.assertIn('Submission', json.dumps(plan['planning_horizon']))

    def test_unspecified_export_material_choice_blocks_without_invented_format(self):
        def produce(context):
            data = goal(context)
            turn = context.current_turn
            data['ambiguities'] = [{'topic': 'export format', 'description': 'Which export format is required?',
                'decision_owner': 'user', 'materiality': 'MEDIUM', 'candidate_interpretations': [],
                'evidence': [span_payload(asdict(claim(turn, IntentKind.GOAL, 'Export', turn.raw_text, 'export').evidence[0]))]}]
            return data
        status, output, errors = self.run_cli('帮我增加导出功能。', Client(produce))
        self.assertEqual(status, 0, errors)
        plan = json.loads(output.split('Planning:\n')[1])
        self.assertFalse(plan['success'])
        self.assertIsNone(plan['agent_task_package'])
        specification = json.loads(output.split('Intent Specification / Readiness:\n')[1].split('Planning:\n')[0])['specification']
        self.assertNotIn('CSV', json.dumps(specification['user_decisions']))

    def test_revision_uses_bounded_context_and_preserves_old_snapshot(self):
        conv = conversation('实现作业提交。')
        first = interpret_conversation(conv, ModelBackedSemanticInterpreter(Client(goal)))
        old = build_intent_specification(first)
        conv.add_turn('user', '算了，提交先不做，我想先把截止日期做好。')
        def revise(context):
            self.assertEqual(context.intent_summary.goal, '实现作业提交。')
            self.assertEqual(context.recent_turns[0].raw_text, '实现作业提交。')
            turn = context.current_turn
            return result(context,
                claim(turn, IntentKind.GOAL, 'Implement assignment deadlines.', '把截止日期做好', 'deadline'),
                claim(turn, IntentKind.SCOPE_OUT, 'Submission', '提交先不做', 'submission'))
        new = build_intent_specification(interpret_conversation(conv,
            ModelBackedSemanticInterpreter(Client(revise), current_intent=first.current_intent)), previous=old)
        self.assertEqual(new.supersedes, old.id)
        self.assertEqual(new.version, old.version + 1)
        self.assertEqual(old.goal.value, '实现作业提交。')
        plan = Planner().plan(new, ProjectContext())
        self.assertTrue(plan.success)
        self.assertNotIn('Submission', json.dumps(asdict(plan.current_work_unit)['scope_in']))
        self.assertEqual(len(conv.turns), 2)

    def test_bad_evidence_is_rejected_in_normal_runtime(self):
        for edit in (
            lambda ref: ref.update(turn_id='unknown'),
            lambda ref: ref.update(start=-1),
            lambda ref: ref.update(end=9999),
            lambda ref: ref.update(turn_id='README.md'),
        ):
            def produce(context):
                data = goal(context)
                data = json.loads(json.dumps(data))
                edit(data['claims'][0]['evidence'][0])
                return data
            status, output, errors = self.run_cli('Add search.', Client(produce))
            self.assertEqual(status, 1)
            failure = json.loads(output.split('Interpretation Failure:\n')[1])
            self.assertEqual(failure['category'], 'EvidenceValidationFailure')
            self.assertEqual(failure['conversation']['turns'][0]['raw_text'], 'Add search.')
            self.assertNotIn('Intent Specification / Readiness:', output)

    def test_jia_and_hidden_old_turns_cannot_be_cited(self):
        conv = conversation('old request')
        old = conv.turns[0]
        for _ in range(5):
            conv.add_turn('jia', 'suggestion')
        jia = conv.turns[-1]
        conv.add_turn('user', 'current request')
        for cited in (old, jia):
            client = Client(lambda context: result(context,
                claim(cited, IntentKind.GOAL, 'Invented', cited.raw_text, 'bad')))
            with self.assertRaises(EvidenceValidationFailure):
                interpret_conversation(conv, ModelBackedSemanticInterpreter(client))

    def test_project_fact_is_advisory_and_cannot_be_user_evidence(self):
        conv = conversation('Keep authentication unchanged.')
        def produce(context):
            self.assertEqual(context.project_facts[0].value, 'Authentication uses JWT.')
            data = json.loads(json.dumps(goal(context)))
            data['claims'][0]['evidence'][0] = {
                'turn_id': 'auth.py', 'start': 0, 'end': 24}
            return data
        interpreter = ModelBackedSemanticInterpreter(Client(produce),
            project_facts=(ProjectFact('Authentication uses JWT.', 'auth.py'),))
        with self.assertRaises(EvidenceValidationFailure):
            interpret_conversation(conv, interpreter)
        self.assertEqual(conv.turns[0].raw_text, 'Keep authentication unchanged.')

    def test_strict_output_rejects_partial_duplicate_and_nested_authority(self):
        conv = conversation('Add search.')
        context = build_semantic_context(tuple(conv.turns))
        data = json.loads(json.dumps(goal(context)))
        data['claims'][0]['status'] = 'CONFIRMED'
        quoted = json.loads(json.dumps(goal(context)))
        quoted['claims'][0]['evidence'][0]['quote'] = 'Add search.'
        for wire in (json.dumps(data), json.dumps(quoted), '{"claims": [], "claims": []}', '[NaN]', 'x' * 262145):
            client = Mock()
            client.interpret.return_value = SemanticModelResponse(wire)
            with self.assertRaises(ModelOutputFailure):
                interpret_conversation(conv, ModelBackedSemanticInterpreter(client))

    def test_schema_and_authority_fields_cannot_update_intent(self):
        for extra in ({'status': 'CONFIRMED'}, {'readiness': 'READY'}, {'user_decisions': []}, {'claims': []}):
            def produce(context):
                return {**goal(context), **extra}
            status, output, errors = self.run_cli('Add search.', Client(produce))
            self.assertEqual(status, 1)
            self.assertIn('ModelOutputFailure', output)
            self.assertNotIn('Planning:', output)

    def test_invalid_schema_malformed_output_and_transport_never_fallback(self):
        for response in (SemanticModelResponse('{'), SemanticModelResponse('{"claims": []}'),
                         TransportFailure('service_unavailable')):
            client = Mock()
            if isinstance(response, Exception):
                client.interpret.side_effect = response
            else:
                client.interpret.return_value = response
            with patch('mr_moneybags.semantic.default.DeterministicInterpreter.interpret', side_effect=AssertionError('fallback')):
                status, output, errors = self.run_cli('Add search.', client)
            self.assertEqual(status, 1)
            self.assertNotIn('Planning:', output)
            self.assertNotIn('fallback', output + errors)

    def test_conflicting_concept_and_expanded_delegation_are_rejected(self):
        def conflicting(context):
            turn = context.current_turn
            return result(context, claim(turn, IntentKind.GOAL, 'Search', 'Search', 'search'),
                          claim(turn, IntentKind.FUTURE_CONSIDERATION, 'Search', 'Search', 'search'))
        with self.assertRaises(ModelOutputFailure):
            interpret_conversation(conversation('Search'), ModelBackedSemanticInterpreter(Client(conflicting)))
        def expanded(context):
            data = json.loads(json.dumps(goal(context)))
            data['claims'][0]['implementation_delegation'] = 'all_actions_authorized'
            return data
        with self.assertRaises(ModelOutputFailure):
            interpret_conversation(conversation('Search'), ModelBackedSemanticInterpreter(Client(expanded)))
