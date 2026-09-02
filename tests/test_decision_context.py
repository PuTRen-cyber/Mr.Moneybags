from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import unittest
from unittest.mock import patch

from mr_moneybags.cli import main
from mr_moneybags.conversation.models import EvidenceReference, IntentKind, ProjectConversation
from mr_moneybags.context.models import ProjectContext
from mr_moneybags.decision_context import build_decision_context
from mr_moneybags.planning.planner import Planner
from mr_moneybags.reporter import build_codex_brief, build_human_report
from mr_moneybags.semantic.interpreter import interpret_conversation
from mr_moneybags.semantic.models import SemanticClaim, SemanticResult
from mr_moneybags.specification.builder import build_intent_specification


RAW = '课程管理系统增加作业功能。老师可以创建作业，学生可以查看。提交和评分以后再考虑。'


def claim(turn, identifier, kind, value, quote):
    start = turn.raw_text.index(quote)
    evidence = (EvidenceReference(turn.id, start, start + len(quote), quote),)
    return SemanticClaim(identifier, identifier, kind, value, evidence)


def semantic_result(turn):
    return SemanticResult(turn.id, (
        claim(turn, 'goal', IntentKind.GOAL, '增加课程作业功能', '课程管理系统增加作业功能'),
        claim(turn, 'create', IntentKind.SCOPE_IN, '老师可以创建作业', '老师可以创建作业'),
        claim(turn, 'view', IntentKind.SCOPE_IN, '学生可以查看作业', '学生可以查看'),
        claim(turn, 'submission', IntentKind.FUTURE_CONSIDERATION,
              '作业提交功能以后再考虑', '提交和评分以后再考虑'),
    ))


class Interpreter:
    def interpret(self, turns):
        return semantic_result(turns[-1])


def alignment_for(raw=RAW):
    conversation = ProjectConversation()
    conversation.add_turn('user', raw)
    return conversation, interpret_conversation(conversation, Interpreter())


class DecisionContextTest(unittest.TestCase):
    def test_confirmed_scope_and_deferred_scope_out_preserve_provenance(self):
        conversation, alignment = alignment_for()
        context = build_decision_context(alignment)

        self.assertEqual(context.objective.value, '增加课程作业功能')
        self.assertEqual([item.value for item in context.scope_in], ['老师可以创建作业', '学生可以查看作业'])
        self.assertEqual([item.value for item in context.scope_out], ['作业提交功能以后再考虑'])
        self.assertEqual(context.scope_out[0].evidence, alignment.current_intent.future_considerations[0].evidence)
        self.assertNotIn('作业提交功能以后再考虑', [item.value for item in context.confirmed_information])
        self.assertEqual(context.open_user_decisions, ())
        self.assertEqual(context.agent_proposals, ())
        self.assertEqual(conversation.turns[0].raw_text, RAW)

    def test_human_report_and_codex_brief_use_same_decision_state(self):
        _, alignment = alignment_for()
        context = build_decision_context(alignment)
        specification = build_intent_specification(alignment)
        planning = Planner().plan(specification, ProjectContext())

        human = build_human_report(specification, decision_context=context)
        brief = build_codex_brief(planning.agent_task_package, decision_context=context)

        self.assertEqual(human.scope_out, ['作业提交功能以后再考虑'])
        self.assertEqual(brief.constraints, ['Do not include: 作业提交功能以后再考虑'])

    def test_context_does_not_invent_open_decisions_or_agent_proposals(self):
        _, alignment = alignment_for()
        context = build_decision_context(alignment)

        self.assertEqual(context.open_user_decisions, ())
        self.assertEqual(context.agent_proposals, ())
        self.assertIsNone(context.stage)

    def test_runtime_reports_case_b_scope_out_consistently(self):
        output, error = StringIO(), StringIO()
        with patch('builtins.input', return_value=RAW), redirect_stdout(output), redirect_stderr(error):
            status = main(interpreter=Interpreter())

        self.assertEqual(status, 0, error.getvalue())
        rendered = output.getvalue()
        self.assertIn('Scope Out:\n- 作业提交功能以后再考虑', rendered)
        self.assertIn('Do not include: 作业提交功能以后再考虑', rendered)


if __name__ == '__main__':
    unittest.main()
