from dataclasses import FrozenInstanceError, asdict, replace
import json
import unittest
from unittest.mock import patch

from mr_moneybags.conversation.alignment import analyze_conversation
from mr_moneybags.conversation.models import (
    Ambiguity, AmbiguityStatus, Assumption, AssumptionStatus, DecisionOwner,
    IntentStatement, IntentKind, Materiality, ProjectConversation, QuestionRequest,
)
from mr_moneybags.specification.builder import build_intent_specification, supersede_specification
from mr_moneybags.specification.models import BlockingCategory, SpecificationStatus
from mr_moneybags.specification.readiness import evaluate_readiness
from mr_moneybags.task import Task
from mr_moneybags.context.models import ProjectContext, DerivedClaim


class SpecificationTest(unittest.TestCase):
    def conversation(self, *messages):
        conversation = ProjectConversation()
        for text in messages:
            conversation.add_turn('user', text)
        return conversation

    def build(self, *messages):
        return build_intent_specification(analyze_conversation(self.conversation(*messages)))

    def confirm(self, conversation):
        conversation.request_confirmation(analyze_conversation(conversation).current_intent)
        conversation.add_turn('user', 'yes')
        return build_intent_specification(analyze_conversation(conversation))

    def test_preserves_meaning_and_provenance(self):
        alignment = analyze_conversation(self.conversation(
            'I want a parser.', 'Expected outcome: a working parser.',
            'Must preserve behavior.', 'I prefer a simple interface.',
            'Include text input.', 'Exclude web UI.', 'Later add plugins.'))
        spec = build_intent_specification(alignment)
        current = alignment.current_intent
        self.assertEqual(spec.goal, current.goal)
        self.assertEqual(spec.expected_outcome, current.expected_outcome)
        for name in ('constraints', 'preferences', 'scope_in', 'scope_out', 'future_considerations'):
            self.assertEqual(getattr(spec, name), tuple(getattr(current, name)))
        self.assertEqual(spec.source_intent_version, current.revision)
        self.assertTrue(set(current.source_turn_ids) <= set(spec.source_turn_ids))
        self.assertEqual(spec.goal.source_turn_ids, current.goal.source_turn_ids)
        self.assertEqual(spec.trust_level, 'Derived Intent Specification / Interpretation')

    def test_export_is_blocked_without_invented_format(self):
        spec = self.build('I want to add export functionality.')
        result = evaluate_readiness(spec)
        self.assertEqual(spec.status, SpecificationStatus.BLOCKED)
        self.assertFalse(result.ready)
        self.assertIn(BlockingCategory.UNRESOLVED_MATERIAL_AMBIGUITY,
                      [reason.category for reason in result.blocking_reasons])
        self.assertNotIn('CSV', spec.goal.value)
        self.assertEqual(spec.working_assumptions, ())

    def test_internal_refactor_is_ready(self):
        spec = self.build('Refactor the internal authentication helper without changing behavior.')
        result = evaluate_readiness(spec)
        self.assertTrue(result.ready)
        self.assertEqual(spec.status, SpecificationStatus.READY)
        self.assertTrue(spec.constraints)
        self.assertTrue(spec.working_assumptions)
        self.assertEqual(spec.working_assumptions[0].status, AssumptionStatus.ACTIVE)
        self.assertTrue(result.non_blocking_unknowns)

    def test_decisions_and_assumptions_serialize_differently(self):
        spec = self.build('Refactor the internal helper without changing behavior.')
        decision = spec.user_decisions[0]
        assumption = spec.working_assumptions[0]
        self.assertTrue(decision.statement.source_turn_ids)
        self.assertEqual(decision.confirmation_turn_ids, ())
        self.assertNotEqual(set(asdict(decision)), set(asdict(assumption)))
        self.assertNotIn(assumption.id, [item.statement.id for item in spec.user_decisions])

    def test_confirmed_assumption_keeps_its_origin(self):
        spec = self.confirm(self.conversation('Refactor the private helper.'))
        self.assertEqual(spec.working_assumptions[0].status, AssumptionStatus.CONFIRMED)
        self.assertTrue(spec.confirmation_turn_ids)
        self.assertNotIn(spec.working_assumptions[0].id, [d.statement.id for d in spec.user_decisions])

    def test_missing_or_meaningless_goal_blocks(self):
        for text in ('', '...', '???', 'something', 'do it', '随便'):
            with self.subTest(text=text):
                result = evaluate_readiness(self.build(text))
                self.assertFalse(result.ready)
                self.assertIn(BlockingCategory.INSUFFICIENT_GOAL, [r.category for r in result.blocking_reasons])

    def test_optional_empty_fields_do_not_block(self):
        spec = self.build('Add a local parser.')
        self.assertTrue(evaluate_readiness(spec).ready)
        self.assertIsNone(spec.expected_outcome)
        self.assertEqual(spec.preferences, ())
        self.assertEqual(spec.scope_out, ())
        self.assertEqual(spec.future_considerations, ())

    def test_incomplete_internal_rename_is_ready(self):
        spec = self.build('Rename the internal parser class. Keep all external behavior unchanged.')
        self.assertTrue(evaluate_readiness(spec).ready)

    def test_confidence_is_not_a_readiness_gate(self):
        alignment = analyze_conversation(self.conversation('Add a local parser.'))
        alignment.current_intent.goal = replace(alignment.current_intent.goal, confidence=0.01)
        self.assertTrue(evaluate_readiness(build_intent_specification(alignment)).ready)

    def test_high_impact_owners_block_even_without_question(self):
        for owner in (DecisionOwner.USER, DecisionOwner.SHARED):
            alignment = analyze_conversation(self.conversation('Add a local parser.'))
            alignment.ambiguities.append(Ambiguity('high', 'tradeoff', 'Choose the important behavior.', (),
                                                  ('source',), owner, Materiality.HIGH))
            result = evaluate_readiness(build_intent_specification(alignment))
            self.assertFalse(result.ready)
            self.assertIn('source', result.blocking_reasons[0].source_turn_ids)

    def test_required_question_without_ambiguity_blocks(self):
        alignment = analyze_conversation(self.conversation('Add a local parser.'))
        alignment.questions_required.append(QuestionRequest('scope', 'Select scope.', 'missing', Materiality.MEDIUM))
        self.assertFalse(evaluate_readiness(build_intent_specification(alignment)).ready)

    def test_low_implementation_unknown_is_non_blocking(self):
        alignment = analyze_conversation(self.conversation('Add a local parser.'))
        alignment.ambiguities.append(Ambiguity('low', 'helper_naming', 'Private helper name unknown.', (),
                                                  ('source',), DecisionOwner.JIA_AGENT, Materiality.LOW))
        result = evaluate_readiness(build_intent_specification(alignment))
        self.assertTrue(result.ready)
        self.assertEqual(result.non_blocking_unknowns[0].topic, 'helper_naming')

    def test_unsafe_active_assumption_blocks(self):
        for materiality, reversible in ((Materiality.HIGH, True), (Materiality.LOW, False)):
            alignment = analyze_conversation(self.conversation('Add a local parser.'))
            alignment.assumptions.append(Assumption('a', 'Change behavior.', 'Unresolved choice.',
                                                   ('source',), materiality, reversible))
            result = evaluate_readiness(build_intent_specification(alignment))
            self.assertFalse(result.ready)
            self.assertEqual(result.assumptions_in_effect, ())

    def test_rejected_assumption_is_not_in_effect(self):
        alignment = analyze_conversation(self.conversation('Add a local parser.'))
        alignment.assumptions.append(Assumption('a', 'Old assumption.', 'Rejected.', ('source',),
                                               Materiality.LOW, True, AssumptionStatus.REJECTED))
        self.assertEqual(evaluate_readiness(build_intent_specification(alignment)).assumptions_in_effect, ())

    def test_low_assumption_cannot_bypass_high_decision(self):
        alignment = analyze_conversation(self.conversation('Add a local parser.'))
        assumption = Assumption('a', 'Keep existing behavior.', 'Reversible choice.', ('source',), Materiality.LOW, True)
        alignment.assumptions.append(assumption)
        alignment.ambiguities.append(Ambiguity('high', 'behavior', 'Important choice.', (), ('source',),
                                              DecisionOwner.USER, Materiality.HIGH, safe_assumption=assumption))
        result = evaluate_readiness(build_intent_specification(alignment))
        self.assertFalse(result.ready)
        self.assertEqual(result.assumptions_in_effect, ())

    def test_deferred_high_decision_still_blocks(self):
        alignment = analyze_conversation(self.conversation('Add a local parser.'))
        alignment.ambiguities.append(Ambiguity('high', 'tradeoff', 'Important choice.', (), ('source',),
                                              DecisionOwner.SHARED, Materiality.HIGH, status=AmbiguityStatus.DEFERRED))
        self.assertFalse(evaluate_readiness(build_intent_specification(alignment)).ready)

    def test_unrelated_specification_cannot_supersede_history(self):
        old = self.build('Add a local parser.')
        unrelated = self.build('Add a formatter.')
        with self.assertRaises(ValueError):
            supersede_specification(old, unrelated)

    def test_destructive_request_requires_confirmation(self):
        result = evaluate_readiness(self.build('Delete all user data and reset the database.'))
        self.assertFalse(result.ready)
        self.assertIn(BlockingCategory.MISSING_REQUIRED_CONFIRMATION, [r.category for r in result.blocking_reasons])

    def test_valid_destructive_confirmation_can_be_ready(self):
        conversation = self.conversation('Delete all user data and reset the database.')
        spec = self.confirm(conversation)
        self.assertTrue(evaluate_readiness(spec).ready)
        self.assertIn(conversation.turns[-1].id, spec.confirmation_turn_ids)

    def test_stale_confirmation_does_not_unblock(self):
        conversation = self.conversation('Add a local parser.')
        old = analyze_conversation(conversation).current_intent
        conversation.add_turn('user', 'Delete all user data and reset the database.')
        conversation.request_confirmation(old)
        conversation.add_turn('user', 'yes')
        self.assertFalse(evaluate_readiness(build_intent_specification(analyze_conversation(conversation))).ready)

    def test_unresolved_intent_change_blocks(self):
        spec = self.build('Make this web-first.', 'Actually I want desktop to become the primary product.')
        self.assertIn(BlockingCategory.CONFLICTING_USER_INTENT, [r.category for r in spec.blocking_issues])

    def test_resolved_supersession_can_be_ready(self):
        conversation = self.conversation('Make this web-first.', 'Actually I want desktop to become the primary product.')
        self.assertTrue(evaluate_readiness(self.confirm(conversation)).ready)

    def test_active_behavior_contradiction_blocks(self):
        spec = self.build('Do not change authentication behavior.', 'Replace the authentication flow entirely.')
        self.assertFalse(evaluate_readiness(spec).ready)
        reason = next(r for r in spec.blocking_issues if r.category == BlockingCategory.CONFLICTING_USER_INTENT)
        self.assertEqual(len(reason.source_statement_ids), 2)

    def test_behavior_constraint_does_not_block_private_naming(self):
        spec = self.build('Do not change authentication behavior.',
                          'Change the private authentication helper name.')
        self.assertTrue(evaluate_readiness(spec).ready)

    def test_superseded_behavior_constraint_no_longer_blocks(self):
        conversation = self.conversation('Do not change authentication behavior.',
                                         'Replace the authentication flow entirely.',
                                         'Actually Must allow replacing authentication behavior.')
        self.assertTrue(evaluate_readiness(self.confirm(conversation)).ready)

    def test_exact_scope_conflict_blocks(self):
        spec = self.build('Add a tool.', 'Include web UI.', 'Exclude web UI.')
        self.assertIn(BlockingCategory.UNRESOLVED_SCOPE, [r.category for r in spec.blocking_issues])

    def test_ready_snapshot_does_not_follow_mutable_current_intent(self):
        alignment = analyze_conversation(self.conversation('Add a local parser.', 'Must preserve behavior.'))
        spec = build_intent_specification(alignment)
        before = asdict(spec)
        alignment.current_intent.constraints.clear()
        alignment.current_intent.goal = None
        self.assertEqual(asdict(spec), before)
        with self.assertRaises(FrozenInstanceError):
            spec.goal = None

    def test_version_and_supersession_preserve_history(self):
        conversation = self.conversation('Add a local parser.')
        old = build_intent_specification(analyze_conversation(conversation))
        before = asdict(old)
        conversation.add_turn('user', 'Actually I want a local formatter.')
        new = build_intent_specification(analyze_conversation(conversation), previous=old)
        historical = supersede_specification(old, new)
        self.assertEqual(new.version, old.version + 1)
        self.assertNotEqual(new.id, old.id)
        self.assertEqual(new.supersedes, old.id)
        self.assertEqual(historical.status, SpecificationStatus.SUPERSEDED)
        self.assertEqual(historical.superseded_by, new.id)
        self.assertEqual(historical.goal, old.goal)
        self.assertEqual(asdict(old), before)
        with self.assertRaises(ValueError):
            evaluate_readiness(historical)

    def test_deterministic_build_and_serialization(self):
        alignment = analyze_conversation(self.conversation('Add a local parser.'))
        spec = build_intent_specification(alignment)
        self.assertEqual(json.dumps(asdict(spec)), json.dumps(asdict(build_intent_specification(alignment))))
        result = evaluate_readiness(spec)
        self.assertEqual(result.specification_id, spec.id)
        self.assertEqual(result.source_intent_version, spec.source_intent_version)
        json.dumps(asdict(result))

    def test_task_context_and_specification_stay_separate(self):
        task = Task('Add export.')
        context = ProjectContext(detected_technologies=[DerivedClaim('Flask', ['pyproject.toml'])])
        before = (asdict(task), asdict(context))
        spec = self.build(task.raw_input)
        self.assertNotIn('Flask', json.dumps(asdict(spec)))
        self.assertEqual((asdict(task), asdict(context)), before)
        self.assertEqual(task.status, 'NEW')
        self.assertIsNone(self.build().goal)
        for forbidden in ('plan', 'steps', 'prompt', 'codex_prompt', 'task_package'):
            self.assertNotIn(forbidden, asdict(spec))

    def test_builder_and_evaluator_have_no_io(self):
        alignment = analyze_conversation(self.conversation('Delete all user data and reset the database.'))
        before = asdict(alignment)
        with patch('builtins.open', side_effect=AssertionError('Unexpected IO')), \
                patch('subprocess.run', side_effect=AssertionError('Unexpected command')):
            evaluate_readiness(build_intent_specification(alignment))
        self.assertEqual(asdict(alignment), before)
