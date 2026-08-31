from dataclasses import asdict, replace
import json
from io import StringIO
import unittest
from unittest.mock import patch

from mr_moneybags.conversation.models import (
    ProjectConversation, IntentKind, EvidenceReference, ImplementationDelegation,
    DecisionOwner, Materiality,
)
from mr_moneybags.conversation.alignment import analyze_conversation
from mr_moneybags.semantic.models import SemanticClaim, SemanticResult, SemanticAmbiguity
from mr_moneybags.semantic.interpreter import interpret_conversation, SemanticValidationError
from mr_moneybags.specification.builder import build_intent_specification
from mr_moneybags.planning.planner import Planner
from mr_moneybags.context.models import ProjectContext
from mr_moneybags.cli import main


class FixtureInterpreter:
    def __init__(self, result):
        self.result = result

    def interpret(self, turns):
        return self.result


def conversation(text):
    value = ProjectConversation()
    value.add_turn('user', text)
    return value


def claim(turn, kind, value, quote, concept, **fields):
    start = turn.raw_text.index(quote)
    evidence = EvidenceReference(turn.id, start, start + len(quote), quote)
    return SemanticClaim(concept + ':' + kind.value, concept, kind, value, (evidence,), **fields)


def run_semantic(conv, claims, ambiguities=()):
    result = SemanticResult(conv.turns[-1].id, tuple(claims), tuple(ambiguities))
    alignment = interpret_conversation(conv, FixtureInterpreter(result))
    spec = build_intent_specification(alignment)
    return alignment, spec, Planner().plan(spec, ProjectContext())


class SemanticTest(unittest.TestCase):
    def test_documentation_protected_code_boundary_and_paraphrase(self):
        for text, goal_quote, protected in (
            ('把 README 里的安装说明整理得更清楚，不修改项目代码。', '把 README 里的安装说明整理得更清楚', '不修改项目代码'),
            ('只完善 README 的安装指引；源代码保持原样。', '完善 README 的安装指引', '源代码保持原样'),
        ):
            conv = conversation(text)
            turn = conv.turns[0]
            alignment, spec, plan = run_semantic(conv, [
                claim(turn, IntentKind.GOAL, 'Clarify README installation instructions.', goal_quote, 'docs'),
                claim(turn, IntentKind.SCOPE_IN, 'README installation instructions', goal_quote, 'installation'),
                claim(turn, IntentKind.CONSTRAINT, 'Do not modify project code.', protected, 'code', protected_target='project code'),
            ])
            self.assertTrue(plan.success)
            self.assertEqual(len(alignment.statements), 3)
            self.assertEqual(spec.constraints[0].protected_target, 'project code')
            self.assertTrue(any(d.statement.protected_target == 'project code' for d in plan.agent_task_package.user_decisions))
            self.assertEqual(plan.current_work_unit.constraints[0].value, 'Do not modify project code.')

    def test_modern_login_preserves_auth_without_subjectivity_block(self):
        for text, goal_quote, boundary in (
            ('把登录页面做得更现代一点，但认证逻辑不要动。', '把登录页面做得更现代一点', '认证逻辑不要动'),
            ('更新登录界面的视觉呈现，保持原来的身份验证机制。', '更新登录界面的视觉呈现', '保持原来的身份验证机制'),
        ):
            conv = conversation(text)
            turn = conv.turns[0]
            alignment, spec, plan = run_semantic(conv, [
                claim(turn, IntentKind.GOAL, 'Modernize login page presentation.', goal_quote, 'presentation'),
                claim(turn, IntentKind.CONSTRAINT, 'Preserve authentication logic.', boundary, 'auth', protected_target='authentication logic'),
            ])
            self.assertEqual(alignment.questions_required, [])
            self.assertTrue(plan.success)
            self.assertEqual(spec.constraints[0].protected_target, 'authentication logic')
            self.assertTrue(plan.current_work_unit.allowed_agent_discretion)

    def test_explicit_ordinary_delegation_survives_pipeline(self):
        for text, goal_quote, delegation in (
            ('给这个工具增加搜索，具体怎么实现你们决定。', '给这个工具增加搜索', '具体怎么实现你们决定'),
            ('需要检索功能，内部实现方案由开发者选择。', '需要检索功能', '内部实现方案由开发者选择'),
        ):
            conv = conversation(text)
            turn = conv.turns[0]
            _, spec, plan = run_semantic(conv, [
                claim(turn, IntentKind.GOAL, 'Add search capability.', goal_quote, 'search'),
                claim(turn, IntentKind.CONSTRAINT, 'Ordinary implementation choices are delegated within stated scope and constraints.',
                      delegation, 'delegation', implementation_delegation=ImplementationDelegation.ORDINARY_IMPLEMENTATION),
            ])
            self.assertTrue(plan.success)
            self.assertEqual(spec.constraints[0].implementation_delegation, ImplementationDelegation.ORDINARY_IMPLEMENTATION)
            self.assertTrue(any(d.statement.implementation_delegation for d in plan.agent_task_package.user_decisions))

    def test_current_future_separation_and_paraphrase(self):
        for text, goal, create, view, future in (
            ('给课程管理系统增加作业功能。老师可以创建作业，学生可以查看。提交和评分以后再考虑。',
             '给课程管理系统增加作业功能', '老师可以创建作业', '学生可以查看', '提交和评分以后再考虑'),
            ('先做基础作业管理，支持教师发布、学生浏览；交作业与打分留到将来。',
             '先做基础作业管理', '教师发布', '学生浏览', '交作业与打分留到将来'),
        ):
            conv = conversation(text)
            turn = conv.turns[0]
            _, spec, plan = run_semantic(conv, [
                claim(turn, IntentKind.GOAL, 'Add basic assignment capability.', goal, 'assignment'),
                claim(turn, IntentKind.SCOPE_IN, 'Teachers can create assignments.', create, 'create'),
                claim(turn, IntentKind.SCOPE_IN, 'Students can view assignments.', view, 'view'),
                claim(turn, IntentKind.FUTURE_CONSIDERATION, 'Assignment submission', future, 'submission'),
                claim(turn, IntentKind.FUTURE_CONSIDERATION, 'Grading', future, 'grading'),
            ])
            self.assertEqual(plan.mode, 'ROLLING')
            self.assertEqual(len(spec.future_considerations), 2)
            current = json.dumps([asdict(c) for c in (*plan.current_work_unit.scope_in, *plan.current_work_unit.acceptance_criteria)]).lower()
            self.assertNotIn('submission', current)
            self.assertNotIn('grading', current)

    def test_export_without_format_stays_blocked(self):
        conv = conversation('给项目增加导出功能。')
        _, spec, plan = run_semantic(conv, [claim(conv.turns[0], IntentKind.GOAL, 'Add export capability.', '增加导出功能', 'export')])
        self.assertEqual(spec.status, 'BLOCKED')
        self.assertFalse(plan.success)
        self.assertNotIn('CSV', spec.goal.value)

    def test_refactor_regression(self):
        conv = conversation('Refactor the internal authentication helper without changing behavior.')
        spec = build_intent_specification(analyze_conversation(conv))
        plan = Planner().plan(spec, ProjectContext())
        self.assertEqual(spec.status, 'READY')
        self.assertEqual(plan.mode, 'FAST_PATH')
        self.assertEqual(plan.planning_horizon.future_stages, ())

    def test_named_rename_regression(self):
        conv = conversation('Rename the internal parser class to ConfigParser. Do not change its behavior.')
        spec = build_intent_specification(analyze_conversation(conv))
        plan = Planner().plan(spec, ProjectContext())
        self.assertTrue(plan.success)
        self.assertIn('ConfigParser', plan.current_work_unit.objective.value)
        self.assertTrue(plan.current_work_unit.constraints)
        self.assertEqual(plan.mode, 'FAST_PATH')

    def fixture(self):
        conv = conversation('Add a local parser.')
        item = claim(conv.turns[0], IntentKind.GOAL, 'Add a parser.', 'Add a local parser', 'parser')
        return conv, SemanticResult(conv.turns[0].id, (item,))

    def assert_invalid(self, conv, result):
        with self.assertRaises(SemanticValidationError):
            interpret_conversation(conv, FixtureInterpreter(result))

    def test_claim_requires_evidence(self):
        conv, result = self.fixture()
        self.assert_invalid(conv, replace(result, claims=(replace(result.claims[0], evidence=()),)))

    def test_fabricated_quote_and_out_of_bounds_rejected(self):
        conv, result = self.fixture()
        original = result.claims[0]
        for evidence in (replace(original.evidence[0], quote='invented'), replace(original.evidence[0], start=-1),
                         replace(original.evidence[0], end=1000), replace(original.evidence[0], turn_id='missing')):
            self.assert_invalid(conv, replace(result, claims=(replace(original, evidence=(evidence,)),)))

    def test_jia_text_is_not_user_evidence(self):
        conv, result = self.fixture()
        turn = conv.add_turn('jia', 'Add a local parser.')
        evidence = replace(result.claims[0].evidence[0], turn_id=turn.id)
        self.assert_invalid(conv, replace(result, claims=(replace(result.claims[0], evidence=(evidence,)),)))

    def test_stale_semantic_result_rejected(self):
        conv, result = self.fixture()
        conv.add_turn('user', 'Actually add a formatter.')
        self.assert_invalid(conv, result)

    def test_future_cannot_also_be_current_same_concept(self):
        conv, result = self.fixture()
        future = replace(result.claims[0], id='future', kind=IntentKind.FUTURE_CONSIDERATION)
        self.assert_invalid(conv, replace(result, claims=(*result.claims, future)))

    def test_future_and_scope_out_can_share_concept(self):
        conv, result = self.fixture()
        future = replace(result.claims[0], id='future', concept_id='later', kind=IntentKind.FUTURE_CONSIDERATION)
        excluded = replace(future, id='excluded', kind=IntentKind.SCOPE_OUT)
        self.assertTrue(interpret_conversation(conv, FixtureInterpreter(replace(result, claims=(*result.claims, future, excluded)))))

    def test_protected_and_delegation_metadata_only_on_boundaries(self):
        conv, result = self.fixture()
        for fields in ({'protected_target': 'code'}, {'implementation_delegation': ImplementationDelegation.ORDINARY_IMPLEMENTATION}):
            self.assert_invalid(conv, replace(result, claims=(replace(result.claims[0], **fields),)))

    def test_delegation_cannot_encode_unrestricted_authority(self):
        conv, result = self.fixture()
        delegated = replace(result.claims[0], kind=IntentKind.CONSTRAINT, implementation_delegation='all_actions')
        self.assert_invalid(conv, replace(result, claims=(delegated,)))

    def test_explicit_delegation_does_not_remove_high_user_ambiguity(self):
        conv = conversation('增加搜索，实现细节你们决定，但是否发布到公网尚未决定。')
        turn = conv.turns[0]
        goal = claim(turn, IntentKind.GOAL, 'Add search.', '增加搜索', 'search')
        delegation = claim(turn, IntentKind.CONSTRAINT, 'Ordinary implementation is delegated.', '实现细节你们决定',
                           'delegation', implementation_delegation=ImplementationDelegation.ORDINARY_IMPLEMENTATION)
        question = SemanticAmbiguity('publication', 'Public publication is undecided.',
                                    goal.evidence, DecisionOwner.USER, Materiality.HIGH)
        alignment, _, plan = run_semantic(conv, [goal, delegation], [question])
        self.assertTrue(alignment.questions_required)
        self.assertFalse(plan.success)

    def test_low_implementation_ambiguity_does_not_block(self):
        conv, result = self.fixture()
        question = SemanticAmbiguity('implementation', 'Internal organization unspecified.', result.claims[0].evidence,
                                    DecisionOwner.JIA_AGENT, Materiality.LOW)
        alignment = interpret_conversation(conv, FixtureInterpreter(replace(result, ambiguities=(question,))))
        self.assertEqual(alignment.questions_required, [])

    def test_semantic_ambiguity_also_requires_user_evidence(self):
        conv, result = self.fixture()
        question = SemanticAmbiguity('choice', 'Choose an outcome.', (), DecisionOwner.USER, Materiality.MEDIUM)
        self.assert_invalid(conv, replace(result, ambiguities=(question,)))

    def test_semantic_contract_limits_are_enforced(self):
        conv, result = self.fixture()
        self.assert_invalid(conv, replace(result, claims=result.claims * 65))
        self.assert_invalid(conv, replace(result, claims=(replace(result.claims[0], evidence=result.claims[0].evidence * 9),)))

    def test_semantic_adapter_has_no_io_with_test_double(self):
        conv, result = self.fixture()
        with patch('builtins.open', side_effect=AssertionError('Unexpected file read')), \
                patch('subprocess.run', side_effect=AssertionError('Unexpected command')):
            self.assertEqual(interpret_conversation(conv, FixtureInterpreter(result)).current_intent.goal.value, 'Add a parser.')

    def test_serialization_provenance_and_no_automatic_confirmation(self):
        conv, result = self.fixture()
        before = asdict(conv)
        first = interpret_conversation(conv, FixtureInterpreter(result))
        second = interpret_conversation(conv, FixtureInterpreter(result))
        self.assertEqual(json.dumps(asdict(first)), json.dumps(asdict(second)))
        self.assertEqual(first.statements[0].evidence, result.claims[0].evidence)
        self.assertNotEqual(first.current_intent.status, 'CONFIRMED')
        self.assertEqual(asdict(conv), before)

    def test_duplicate_ids_multiple_goals_and_invalid_types_rejected(self):
        conv, result = self.fixture()
        for invalid in (replace(result, claims=(*result.claims, *result.claims)),
                        replace(result, claims=(*result.claims, replace(result.claims[0], id='second'))),
                        replace(result, claims=(replace(result.claims[0], kind='unsupported'),)),
                        replace(result, claims=(replace(result.claims[0], value='  '),))):
            self.assert_invalid(conv, invalid)
        self.assert_invalid(conv, {'claims': []})

    def test_semantic_revision_changes_with_interpretation(self):
        conv, result = self.fixture()
        first = interpret_conversation(conv, FixtureInterpreter(result))
        updated = replace(result, claims=(replace(result.claims[0], value='Add a local text parser.'),))
        second = interpret_conversation(conv, FixtureInterpreter(updated))
        self.assertNotEqual(first.current_intent.revision, second.current_intent.revision)

    def test_cli_accepts_injected_interpreter_without_new_output_section(self):
        class Interpreter:
            def interpret(self, turns):
                return SemanticResult(turns[-1].id, (
                    claim(turns[-1], IntentKind.GOAL, 'Clarify installation instructions.', '整理安装文档', 'docs'),
                    claim(turns[-1], IntentKind.CONSTRAINT, 'Do not modify project code.', '代码不变', 'code', protected_target='project code'),
                ))
        output = StringIO()
        with patch('builtins.input', return_value='整理安装文档，代码不变。'), patch('sys.stdout', output):
            status = main(interpreter=Interpreter())
        self.assertEqual(status, 0)
        planning = json.loads(output.getvalue().split('Planning:\n', 1)[1])
        self.assertTrue(planning['success'])
        self.assertTrue(any(d['statement'].get('protected_target') == 'project code'
                            for d in planning['agent_task_package']['user_decisions']))
        self.assertNotIn('Semantic Provider:', output.getvalue())

    def test_cli_validation_failure_stops_before_specification(self):
        output, error = StringIO(), StringIO()
        with patch('builtins.input', return_value='Add a parser.'), patch('sys.stdout', output), patch('sys.stderr', error):
            status = main(interpreter=FixtureInterpreter(SemanticResult('stale', ())))
        self.assertEqual(status, 1)
        self.assertIn('stale_source_turn', error.getvalue())
        self.assertNotIn('Planning:\n', output.getvalue())

    def test_default_cli_omits_empty_semantic_metadata(self):
        output = StringIO()
        with patch('builtins.input', return_value='Add a local parser.'), patch('sys.stdout', output):
            self.assertEqual(main(), 0)
        self.assertNotIn('"protected_target": null', output.getvalue())
        self.assertNotIn('"implementation_delegation": null', output.getvalue())
        self.assertNotIn('"evidence": []', output.getvalue())
