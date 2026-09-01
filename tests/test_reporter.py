from dataclasses import asdict
import unittest

from mr_moneybags.conversation.models import IntentKind, IntentStatement
from mr_moneybags.planning.models import AgentTaskPackage, ContextSummary, PlanningClaim
from mr_moneybags.reporter import build_codex_brief, build_human_report
from mr_moneybags.safety import RiskLevel, SafetyDecision, SafetyStatus
from mr_moneybags.specification.models import IntentSpecification, SpecificationStatus


def statement(identifier, kind, value):
    return IntentStatement(identifier, kind, value, ('turn-1',), 0.9)


def claim(value):
    return PlanningClaim(value, ('turn-1',), 'user_intent')


def specification(goal='Add homework management basics.'):
    goal_statement = statement('goal', IntentKind.GOAL, goal) if goal is not None else None
    return IntentSpecification(
        id='spec-1', version=3, goal=goal_statement, source_intent_version='intent-2',
        scope_in=(statement('create', IntentKind.SCOPE_IN, 'Teachers can create homework.'),
                  statement('view', IntentKind.SCOPE_IN, 'Students can view homework.')),
        scope_out=(statement('submit', IntentKind.SCOPE_OUT, 'Homework submission.'),
                   statement('grade', IntentKind.SCOPE_OUT, 'Homework grading.')),
        constraints=(statement('auth', IntentKind.CONSTRAINT, 'Do not change authentication.'),),
        status=SpecificationStatus.READY if goal is not None else SpecificationStatus.BLOCKED,
    )


def package(objective='Add homework creation and viewing capability.'):
    return AgentTaskPackage(
        id='package-7', version=4, task_title='Add homework management basics', objective=claim(objective),
        why=claim('Teachers and students need basic homework workflows.'),
        project_context_summary=ContextSummary((), (), (), 'internal trust'),
        scope_in=(claim('Teachers can create homework.'), claim('Students can view homework.')),
        scope_out=(claim('Homework submission.'), claim('Homework grading.')),
        constraints=(claim('Do not change authentication.'),),
        behavior_requirements=(claim('Homework remains visible after creation.'),),
        acceptance_criteria=(claim('Homework creation works.'), claim('Homework viewing works.')),
        verification_expectations=(claim('Add relevant tests.'), claim('Run existing tests.')),
        working_assumptions=(), user_decisions=(),
        allowed_agent_discretion=(claim('Choose internal names within the stated constraints.'),),
        source_specification_id='spec-1', source_specification_version=3, source_stage_id='stage-2',
        source_work_unit_id='unit-6', provenance=('turn-1', 'PROJECT.md'),
    )


class ReporterTest(unittest.TestCase):
    def test_intent_specification_becomes_human_report(self):
        decision = SafetyDecision(SafetyStatus.ALLOW, RiskLevel.LOW, [], [])
        report = build_human_report(specification(), decision)
        self.assertEqual(report.summary, 'Add homework management basics.')
        self.assertEqual(report.scope_in, ['Teachers can create homework.', 'Students can view homework.'])
        self.assertEqual(report.scope_out, ['Homework submission.', 'Homework grading.'])
        self.assertEqual(report.risk, 'LOW')
        self.assertEqual(report.status, 'READY')

    def test_agent_task_package_becomes_codex_brief(self):
        decision = SafetyDecision(SafetyStatus.REQUIRE_CONFIRMATION, RiskLevel.HIGH,
                                  ['Sensitive system area requires confirmation before delegation.'],
                                  ['sensitive_areas'])
        brief = build_codex_brief(package(), decision)
        self.assertEqual(brief.task_title, 'Add homework management basics')
        self.assertEqual(brief.objective, 'Add homework creation and viewing capability.')
        self.assertEqual(brief.requirements, ['Teachers can create homework.', 'Students can view homework.',
                                             'Homework remains visible after creation.'])
        self.assertEqual(brief.acceptance_criteria, ['Homework creation works.', 'Homework viewing works.'])
        self.assertEqual(brief.verification, ['Add relevant tests.', 'Run existing tests.'])
        self.assertEqual(brief.risk_notes, ['Sensitive system area requires confirmation before delegation.'])

    def test_explicit_constraints_and_exclusions_are_preserved(self):
        brief = build_codex_brief(package())
        self.assertEqual(brief.constraints, ['Do not change authentication.',
                                             'Do not include: Homework submission.',
                                             'Do not include: Homework grading.'])
        self.assertEqual(brief.implementation_guidance,
                         ['Choose internal names within the stated constraints.'])

    def test_internal_metadata_is_not_exposed(self):
        payload = asdict(build_codex_brief(package(), SafetyDecision(
            SafetyStatus.REQUIRE_CONFIRMATION, RiskLevel.HIGH, ['Confirm first.'], ['internal_rule'])))
        serialized = repr(payload)
        for hidden in ('source_ids', 'provenance', 'version', 'trust_level', 'matched_rules', 'confidence', 'turn-1'):
            self.assertNotIn(hidden, serialized)

    def test_insufficient_input_is_safe(self):
        report = build_human_report(specification(None))
        self.assertEqual(report.summary, 'Task objective is insufficient.')
        self.assertEqual(report.status, 'BLOCKED')
        brief = build_codex_brief(package('   '))
        self.assertEqual(brief.objective, 'Task objective is insufficient.')

    def test_source_objects_are_not_modified(self):
        spec = specification()
        task_package = package()
        before = asdict(spec), asdict(task_package)
        build_human_report(spec)
        build_codex_brief(task_package)
        self.assertEqual((asdict(spec), asdict(task_package)), before)


if __name__ == '__main__':
    unittest.main()
