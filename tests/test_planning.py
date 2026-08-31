from dataclasses import asdict, replace, FrozenInstanceError
import json
import unittest
from unittest.mock import patch

from mr_moneybags.context.models import ProjectContext, DerivedClaim, SourceArtifact
from mr_moneybags.conversation.alignment import analyze_conversation
from mr_moneybags.conversation.models import ProjectConversation, AssumptionStatus
from mr_moneybags.specification.builder import build_intent_specification
from mr_moneybags.specification.models import SpecificationStatus
from mr_moneybags.planning.planner import Planner, supersede_plan


def specification(*messages, previous=None):
    conversation = ProjectConversation()
    for message in messages:
        conversation.add_turn('user', message)
    return build_intent_specification(analyze_conversation(conversation), previous=previous)


def assignment_specification():
    return specification('Add basic assignment functionality.',
                         'Include teacher creation of assignments.',
                         'Include student viewing of assignments.',
                         'Include assignments belonging to courses.',
                         'Exclude submissions.', 'Exclude grading.', 'Exclude notifications.',
                         'Later consider submissions.', 'Later consider grading.')


class PlanningTest(unittest.TestCase):
    def plan(self, spec, context=None, previous=None):
        return Planner().plan(spec, context or ProjectContext(), previous=previous)

    def test_non_ready_specifications_have_no_package(self):
        spec = specification('Add export.')
        for status in (SpecificationStatus.BLOCKED, SpecificationStatus.DRAFT, SpecificationStatus.SUPERSEDED):
            result = self.plan(replace(spec, status=status))
            self.assertFalse(result.success)
            self.assertTrue(result.blocking_reasons)
            self.assertIsNone(result.agent_task_package)
            self.assertIsNone(result.current_work_unit)
            self.assertIsNone(result.planning_horizon)

    def test_ready_label_does_not_bypass_readiness_blockers(self):
        result = self.plan(replace(specification('Add export.'), status=SpecificationStatus.READY))
        self.assertFalse(result.success)
        self.assertIsNone(result.agent_task_package)

    def test_refactor_fast_path(self):
        spec = specification('Refactor the internal authentication helper without changing behavior.')
        result = self.plan(spec)
        self.assertTrue(result.success)
        self.assertEqual(result.mode, 'FAST_PATH')
        self.assertEqual(result.planning_horizon.future_stages, ())
        self.assertEqual(result.planning_horizon.current_stage.status, 'CURRENT')
        self.assertEqual(result.agent_task_package.status, 'READY_FOR_DELEGATION')
        self.assertTrue(any('behavior' in item.value for item in result.current_work_unit.scope_out))

    def test_parser_rename_has_one_work_unit(self):
        result = self.plan(specification('Rename the internal parser class while preserving external behavior.'))
        self.assertEqual(result.mode, 'FAST_PATH')
        self.assertIn('parser', result.current_work_unit.objective.value)
        self.assertEqual(result.planning_horizon.future_stages, ())
        self.assertNotIn('work_units', asdict(result))

    def test_assignment_rolling_keeps_coherent_current_capability(self):
        result = self.plan(assignment_specification())
        self.assertTrue(result.success)
        self.assertEqual(result.mode, 'ROLLING')
        self.assertEqual(len(result.current_work_unit.scope_in), 3)
        current = ' '.join(item.value for item in result.current_work_unit.scope_in)
        for capability in ('teacher', 'student', 'courses'):
            self.assertIn(capability, current)
        future = ' '.join(stage.objective.value for stage in result.planning_horizon.future_stages)
        self.assertIn('submissions', future)
        self.assertIn('grading', future)
        self.assertNotIn('notifications', future)
        self.assertNotIn('grading', current)

    def test_future_stages_are_coarse_and_not_committed(self):
        result = self.plan(assignment_specification())
        for stage in result.planning_horizon.future_stages:
            self.assertEqual(stage.status, 'FUTURE')
            self.assertFalse(stage.committed)
            for field in ('files', 'commands', 'steps', 'work_unit', 'acceptance_criteria'):
                self.assertNotIn(field, asdict(stage))
        self.assertEqual(result.current_work_unit.source_stage_id, result.planning_horizon.current_stage.id)

    def test_no_invented_future_for_basic_assignment(self):
        result = self.plan(specification('Add basic assignment functionality.'))
        self.assertEqual(result.mode, 'FAST_PATH')
        self.assertEqual(result.planning_horizon.future_stages, ())
        output = json.dumps(asdict(result)).lower()
        for invented in ('notifications', 'grading', 'calendar', 'email reminders'):
            self.assertNotIn(invented, output)

    def test_negative_preservation_does_not_create_opposite_boundary(self):
        result = self.plan(specification('Replace local parser behavior.', 'Do not preserve existing behavior.'))
        self.assertTrue(result.success)
        self.assertFalse(any('No redesign' in item.value for item in result.current_work_unit.scope_out))

    def test_future_only_consideration_is_excluded_from_current(self):
        result = self.plan(specification('Add a local parser.', 'Later add a web UI.'))
        self.assertFalse(any('web UI' in c.value for c in result.current_work_unit.scope_in))
        self.assertTrue(any('web UI' in c.value for c in result.current_work_unit.scope_out))

    def test_horizon_stays_coarse_without_losing_explicit_future_sources(self):
        spec = specification('Add a local parser.', *[f'Later consider capability {i}.' for i in range(7)])
        result = self.plan(spec)
        self.assertLessEqual(len(result.planning_horizon.future_stages), 3)
        future_sources = {s for stage in result.planning_horizon.future_stages for s in stage.source_ids}
        self.assertTrue({item.id for item in spec.future_considerations} <= future_sources)

    def test_package_preserves_work_unit_conditions(self):
        spec = specification('Add a local parser.', 'Must preserve compatibility.',
                             'When input is empty return no records.', 'Expected outcome: parse local text.',
                             'I prefer a simple interface.')
        result = self.plan(spec)
        unit, package = result.current_work_unit, result.agent_task_package
        for field in ('objective', 'scope_in', 'scope_out', 'constraints', 'behavior_requirements',
                      'acceptance_criteria', 'verification_expectations', 'allowed_agent_discretion'):
            self.assertEqual(getattr(package, field), getattr(unit, field))
        self.assertTrue(unit.acceptance_criteria)
        self.assertTrue(unit.behavior_requirements)
        self.assertEqual(package.user_decisions, spec.user_decisions)
        self.assertTrue(any(item.statement.kind == 'preference' for item in package.user_decisions))

    def test_assumptions_stay_separate(self):
        spec = specification('Refactor the private helper without changing behavior.')
        result = self.plan(spec)
        self.assertEqual(result.agent_task_package.working_assumptions, spec.working_assumptions)
        self.assertEqual(result.agent_task_package.working_assumptions[0].status, AssumptionStatus.ACTIVE)
        self.assertNotIn(spec.working_assumptions[0].id, [d.statement.id for d in result.agent_task_package.user_decisions])

    def test_agent_discretion_remains_internal_and_conditional(self):
        unit = self.plan(specification('Refactor the private helper.')).current_work_unit
        text = ' '.join(item.value for item in unit.allowed_agent_discretion)
        self.assertIn('private helper names', text)
        self.assertIn('implementation sequence', text)
        self.assertIn('scope and constraints', text)

    def test_context_is_evidence_not_user_preference(self):
        context = ProjectContext(detected_technologies=[DerivedClaim('Flask', ['pyproject.toml'])],
                                 test_commands=[DerivedClaim('python -m unittest', ['README.md'])],
                                 sources=[SourceArtifact('README.md', 'abc', 20)])
        spec = specification('Add a local parser.')
        result = self.plan(spec, context)
        package = result.agent_task_package
        self.assertIn('Flask', json.dumps(asdict(package.project_context_summary)))
        self.assertNotIn('Flask', json.dumps(asdict(package.objective)))
        self.assertEqual(package.user_decisions, spec.user_decisions)
        self.assertIn('README.md', result.planning_horizon.source_context_sources)
        self.assertTrue(any('existing test approach' in c.value for c in package.verification_expectations))

    def test_provenance_links_specification_statements_assumptions_and_context(self):
        spec = specification('Refactor the private helper without changing behavior.')
        result = self.plan(spec)
        package = result.agent_task_package
        self.assertEqual(package.source_specification_id, spec.id)
        self.assertEqual(package.source_specification_version, spec.version)
        self.assertEqual(package.source_work_unit_id, result.current_work_unit.id)
        self.assertEqual(package.source_stage_id, result.planning_horizon.current_stage.id)
        self.assertIn(spec.goal.id, package.objective.source_ids)
        self.assertIn(spec.working_assumptions[0].id, package.provenance)

    def test_briefing_is_plain_dispatch_preview(self):
        result = self.plan(assignment_specification())
        briefing = result.stage_briefing
        self.assertEqual(briefing.objective, result.current_work_unit.objective.value)
        self.assertEqual(briefing.in_scope, tuple(c.value for c in result.current_work_unit.scope_in))
        self.assertEqual(briefing.out_of_scope, tuple(c.value for c in result.current_work_unit.scope_out))
        self.assertEqual(briefing.done_when, tuple(c.value for c in result.current_work_unit.acceptance_criteria))
        self.assertNotIn('source_ids', asdict(briefing))

    def test_package_is_agent_independent_and_not_executing(self):
        package = self.plan(specification('Add a local parser.')).agent_task_package
        serialized = json.dumps(asdict(package)).lower()
        for forbidden in ('codex', 'openai', 'reasoning_effort', 'run this command', 'model_provider'):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(package.status, 'READY_FOR_DELEGATION')

    def test_deterministic_serialization(self):
        spec = assignment_specification()
        self.assertEqual(json.dumps(asdict(self.plan(spec))), json.dumps(asdict(self.plan(spec))))

    def test_context_mutation_cannot_change_historical_package(self):
        context = ProjectContext(detected_technologies=[DerivedClaim('Python', ['pyproject.toml'])])
        result = self.plan(specification('Add a local parser.'), context)
        before = asdict(result)
        context.detected_technologies[0].sources.clear()
        context.detected_technologies[0].value = 'Other'
        self.assertEqual(asdict(result), before)
        with self.assertRaises(FrozenInstanceError):
            result.agent_task_package.objective = None

    def test_supersession_preserves_all_historical_meaning(self):
        old_spec = specification('Add a local parser.')
        old = self.plan(old_spec)
        before = asdict(old)
        new_spec = specification('Add a local formatter.', previous=old_spec)
        new = self.plan(new_spec, previous=old)
        history = supersede_plan(old, new)
        self.assertEqual(new.agent_task_package.version, old.agent_task_package.version + 1)
        self.assertEqual(history.agent_task_package.status, 'SUPERSEDED')
        self.assertEqual(history.planning_horizon.status, 'SUPERSEDED')
        self.assertEqual(history.planning_horizon.current_stage.status, 'SUPERSEDED')
        self.assertEqual(history.current_work_unit.status, 'SUPERSEDED')
        self.assertEqual(history.agent_task_package.objective, old.agent_task_package.objective)
        self.assertEqual(asdict(old), before)

    def test_unrelated_specification_cannot_replace_plan(self):
        old = self.plan(specification('Add a parser.'))
        result = self.plan(specification('Add a formatter.'), previous=old)
        self.assertFalse(result.success)

    def test_failed_plan_cannot_supersede_history(self):
        old = self.plan(specification('Add a parser.'))
        failed = self.plan(specification('Add export.'))
        with self.assertRaises(ValueError):
            supersede_plan(old, failed)

    def test_planning_has_no_io_and_does_not_mutate_inputs(self):
        spec, context = assignment_specification(), ProjectContext()
        before = asdict(spec), asdict(context)
        with patch('builtins.open', side_effect=AssertionError('Unexpected IO')), \
                patch('subprocess.run', side_effect=AssertionError('Unexpected command')):
            self.plan(spec, context)
        self.assertEqual((asdict(spec), asdict(context)), before)
