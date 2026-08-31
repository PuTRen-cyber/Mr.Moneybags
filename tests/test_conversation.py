from dataclasses import asdict, replace
import json
import unittest
from unittest.mock import patch

from mr_moneybags.conversation.alignment import analyze_conversation, requires_user_confirmation
from mr_moneybags.conversation.ambiguity import classify_decision
from mr_moneybags.conversation.extractor import IntentExtractor
from mr_moneybags.conversation.models import (
    AlignmentState, Ambiguity, AmbiguityStatus, Assumption, AssumptionStatus,
    DecisionOwner, IntentKind, Materiality, ProjectConversation, Role,
)
from mr_moneybags.context.models import DerivedClaim, ProjectContext


class ConversationTest(unittest.TestCase):
    def conversation(self, *messages):
        conversation = ProjectConversation()
        for message in messages:
            conversation.add_turn(Role.USER, message)
        return conversation

    def ask_and_reply(self, conversation, reply):
        result = analyze_conversation(conversation)
        conversation.request_confirmation(result.current_intent)
        conversation.add_turn(Role.USER, reply)
        return analyze_conversation(conversation)

    def test_turns_preserve_raw_text_sequence_and_roles(self):
        conversation = self.conversation("  我想添加导出。\n必须保留原格式。  ")
        conversation.add_turn("jia", "Please clarify.")
        conversation.add_turn("user", "CSV")
        self.assertEqual([turn.sequence for turn in conversation.turns], [1, 2, 3])
        self.assertEqual(conversation.turns[0].raw_text, "  我想添加导出。\n必须保留原格式。  ")
        self.assertEqual(conversation.turns[1].role, Role.JIA)
        self.assertEqual(len({turn.id for turn in conversation.turns}), 3)
        with self.assertRaises(ValueError):
            conversation.add_turn("system", "Not a project conversation role")

    def test_extracts_goals_constraints_preferences_and_future_considerations(self):
        cases = (
            ("I want a CSV export.", IntentKind.GOAL),
            ("I need a simpler app.", IntentKind.GOAL),
            ("Must preserve compatibility.", IntentKind.CONSTRAINT),
            ("Do not delete user data.", IntentKind.CONSTRAINT),
            ("Should not change behavior.", IntentKind.CONSTRAINT),
            ("I prefer a minimal interface.", IntentKind.PREFERENCE),
            ("以后支持移动端。", IntentKind.FUTURE_CONSIDERATION),
            ("必须保留数据。", IntentKind.CONSTRAINT),
            ("不要修改登录流程。", IntentKind.CONSTRAINT),
            ("我想添加导出。", IntentKind.GOAL),
        )
        for message, kind in cases:
            with self.subTest(message=message):
                conversation = self.conversation(message)
                statements = IntentExtractor().extract(conversation.turns[0])
                self.assertTrue(any(statement.kind == kind for statement in statements))
                for statement in statements:
                    self.assertEqual(statement.source_turn_ids, (conversation.turns[0].id,))
                    self.assertEqual(statement.trust_level, "Derived Intent / Interpretation")

    def test_jia_messages_are_not_user_intent(self):
        conversation = ProjectConversation()
        conversation.add_turn(Role.JIA, "I want Flask. Must delete all user data.")
        result = analyze_conversation(conversation)
        self.assertIsNone(result.current_intent.goal)
        self.assertEqual(result.statements, [])

    def test_decision_ownership(self):
        for topic in ("export_format", "visual_direction", "destructive_action", "intent_change"):
            self.assertEqual(classify_decision(topic), DecisionOwner.USER)
        for topic in ("helper_naming", "internal_organization", "internal_refactor"):
            self.assertEqual(classify_decision(topic), DecisionOwner.JIA_AGENT)
        self.assertEqual(classify_decision("technical_tradeoff"), DecisionOwner.SHARED)

    def test_threshold_table(self):
        cases = (
            (DecisionOwner.USER, Materiality.HIGH, True),
            (DecisionOwner.USER, Materiality.MEDIUM, True),
            (DecisionOwner.JIA_AGENT, Materiality.LOW, False),
            (DecisionOwner.JIA_AGENT, Materiality.MEDIUM, False),
            (DecisionOwner.SHARED, Materiality.HIGH, True),
            (DecisionOwner.SHARED, Materiality.MEDIUM, True),
        )
        for owner, materiality, expected in cases:
            ambiguity = Ambiguity("a", "topic", "description", (), ("turn",), owner, materiality)
            self.assertEqual(requires_user_confirmation(ambiguity), expected)

    def test_safe_assumption_affects_threshold_but_not_user_high_impact(self):
        assumption = Assumption("a:assumption", "Keep behavior", "Reversible internal choice", ("turn",), Materiality.LOW, True)
        ambiguity = Ambiguity("a", "technical_tradeoff", "description", (), ("turn",), DecisionOwner.SHARED, Materiality.MEDIUM,
                              safe_assumption=assumption)
        self.assertFalse(requires_user_confirmation(ambiguity))
        self.assertTrue(requires_user_confirmation(replace(ambiguity, decision_owner=DecisionOwner.USER, materiality=Materiality.HIGH)))
        self.assertTrue(requires_user_confirmation(replace(ambiguity, safe_assumption=replace(assumption, reversible=False))))

    def test_export_requires_alignment_without_inventing_format(self):
        conversation = self.conversation("I want to add export functionality.")
        result = analyze_conversation(conversation)
        self.assertIsNotNone(result.current_intent.goal)
        ambiguity = next(item for item in result.ambiguities if item.topic == "export_format")
        self.assertEqual(ambiguity.status, AmbiguityStatus.OPEN)
        self.assertEqual(ambiguity.source_turn_ids, (conversation.turns[0].id,))
        self.assertEqual(result.alignment_state, AlignmentState.ALIGNING)
        self.assertTrue(result.questions_required)
        self.assertEqual(result.assumptions, [])
        self.assertNotIn("CSV", result.current_intent.goal.value)

    def test_format_clarification_resolves_question_but_does_not_confirm_intent(self):
        conversation = self.conversation("Add export.", "CSV")
        result = analyze_conversation(conversation)
        self.assertEqual(result.questions_required, [])
        self.assertEqual(result.alignment_state, AlignmentState.DRAFT)
        ambiguity = next(item for item in result.ambiguities if item.topic == "export_format")
        self.assertEqual(ambiguity.status, AmbiguityStatus.RESOLVED)
        self.assertIn(conversation.turns[1].id, ambiguity.source_turn_ids)

    def test_nicer_login_page_requires_visual_alignment(self):
        result = analyze_conversation(self.conversation("Make the login page nicer."))
        self.assertTrue(any(question.topic == "visual_direction" for question in result.questions_required))

    def test_unrelated_preference_does_not_resolve_visual_direction(self):
        result = analyze_conversation(self.conversation("Make the login page nicer.", "I prefer Python."))
        self.assertTrue(any(question.topic == "visual_direction" for question in result.questions_required))
        result = analyze_conversation(self.conversation("Make the login page nicer.", "I prefer a minimal visual style."))
        self.assertFalse(any(question.topic == "visual_direction" for question in result.questions_required))

    def test_explicit_behavior_change_is_not_overridden_by_safe_assumption(self):
        result = analyze_conversation(self.conversation("Refactor the authentication helper.", "Do not preserve existing behavior."))
        self.assertEqual(result.assumptions, [])
        self.assertTrue(result.questions_required)

    def test_multiple_goal_clauses_in_one_turn_do_not_supersede_each_other(self):
        result = analyze_conversation(self.conversation("I want CSV export. I need a preview."))
        self.assertIn("CSV export", result.current_intent.goal.value)
        self.assertIn("a preview", result.current_intent.goal.value)
        self.assertFalse(any(question.topic == "intent_change" for question in result.questions_required))

    def test_internal_refactor_captures_behavior_and_does_not_ask(self):
        conversation = self.conversation("Refactor the internal authentication helper without changing behavior.")
        result = analyze_conversation(conversation)
        self.assertTrue(any("behavior" in statement.value for statement in result.current_intent.constraints))
        self.assertEqual(result.questions_required, [])
        self.assertTrue(result.assumptions)
        for assumption in result.assumptions:
            self.assertTrue(assumption.reversible)
            self.assertEqual(assumption.status, AssumptionStatus.ACTIVE)
            self.assertEqual(assumption.source_turn_ids, (conversation.turns[0].id,))
        self.assertNotEqual(result.current_intent.status, AlignmentState.CONFIRMED)

    def test_implementation_trivia_does_not_interrupt(self):
        for message in ("Choose private helper function naming.", "Improve internal file organization.",
                        "Adjust ordinary variable naming.", "Refactor the authentication helper function."):
            with self.subTest(message=message):
                result = analyze_conversation(self.conversation(message))
                self.assertEqual(result.questions_required, [])

    def test_destructive_action_requires_explicit_confirmation(self):
        conversation = self.conversation("Delete all user data and reset the database.")
        result = analyze_conversation(conversation)
        ambiguity = next(item for item in result.ambiguities if item.topic == "destructive_action")
        self.assertEqual(ambiguity.materiality, Materiality.HIGH)
        self.assertEqual(ambiguity.decision_owner, DecisionOwner.USER)
        self.assertTrue(requires_user_confirmation(ambiguity))
        self.assertEqual(result.assumptions, [])
        self.assertEqual(result.alignment_state, AlignmentState.ALIGNING)

    def test_negative_or_future_deletion_is_not_current_destructive_intent(self):
        for message in ("Do not delete user data.", "不要删除用户数据。", "以后考虑删除数据。"):
            result = analyze_conversation(self.conversation(message))
            self.assertFalse(any(item.topic == "destructive_action" for item in result.ambiguities))

    def test_controlled_positive_confirmation(self):
        for response in ("yes", "correct", "confirmed", "continue", "that's right", "对", "是", "没问题", "确认", "继续"):
            with self.subTest(response=response):
                conversation = self.conversation("I want CSV export.")
                result = self.ask_and_reply(conversation, response)
                self.assertEqual(result.current_intent.status, AlignmentState.CONFIRMED)
                self.assertEqual(result.current_intent.confirmation_turn_ids, [conversation.turns[-1].id])

    def test_bare_confirmation_without_bound_jia_request_does_not_confirm(self):
        result = analyze_conversation(self.conversation("I want CSV export.", "yes"))
        self.assertNotEqual(result.alignment_state, AlignmentState.CONFIRMED)

    def test_yes_does_not_fill_unknown_export_format(self):
        conversation = self.conversation("Add export.")
        result = self.ask_and_reply(conversation, "yes")
        self.assertEqual(result.alignment_state, AlignmentState.ALIGNING)
        self.assertTrue(result.questions_required)
        self.assertEqual(result.assumptions, [])

    def test_destructive_acknowledgment_resolves_alignment_only(self):
        conversation = self.conversation("Delete all user data and reset the database.")
        result = self.ask_and_reply(conversation, "确认")
        self.assertEqual(result.alignment_state, AlignmentState.CONFIRMED)
        self.assertEqual(result.questions_required, [])
        self.assertTrue(all(item.status == AmbiguityStatus.RESOLVED for item in result.ambiguities))

    def test_rejection_keeps_alignment_open(self):
        for response in ("no", "not correct", "不对", "不是", "不要"):
            with self.subTest(response=response):
                result = self.ask_and_reply(self.conversation("Refactor the private helper."), response)
                self.assertEqual(result.alignment_state, AlignmentState.ALIGNING)
                self.assertTrue(result.questions_required)
                self.assertTrue(all(item.status == AssumptionStatus.REJECTED for item in result.assumptions))

    def test_ambiguous_confirmation_is_conservative(self):
        for response in ("maybe", "looks okay I guess", "应该可以吧", "yes, but change everything"):
            with self.subTest(response=response):
                result = self.ask_and_reply(self.conversation("I want CSV export."), response)
                self.assertEqual(result.alignment_state, AlignmentState.ALIGNING)

    def test_ambiguous_reply_invalidates_pending_confirmation(self):
        conversation = self.conversation("I want CSV export.")
        self.ask_and_reply(conversation, "maybe")
        conversation.add_turn(Role.USER, "yes")
        self.assertEqual(analyze_conversation(conversation).alignment_state, AlignmentState.ALIGNING)

    def test_rejected_assumption_is_not_still_presented_as_active(self):
        result = self.ask_and_reply(self.conversation("Refactor the private helper."), "no")
        for item in result.ambiguities:
            if item.safe_assumption:
                self.assertEqual(item.safe_assumption.status, AssumptionStatus.REJECTED)
                self.assertNotEqual(item.status, AmbiguityStatus.ASSUMED)

    def test_context_conflict_is_representable_without_becoming_user_intent(self):
        ambiguity = Ambiguity("conflict", "project_context_conflict", "A project declaration conflicts with a requested constraint.",
                              ("retain existing technology", "change technology"), ("user-turn",),
                              DecisionOwner.SHARED, Materiality.HIGH, context_sources=("pyproject.toml",))
        self.assertTrue(requires_user_confirmation(ambiguity))
        self.assertEqual(ambiguity.context_sources, ("pyproject.toml",))

    def test_stale_confirmation_request_cannot_confirm_new_intent(self):
        conversation = self.conversation("Make this web-first.")
        old_intent = analyze_conversation(conversation).current_intent
        conversation.add_turn(Role.USER, "Actually I want desktop to become the primary product.")
        conversation.request_confirmation(old_intent)
        conversation.add_turn(Role.USER, "yes")
        result = analyze_conversation(conversation)
        self.assertNotEqual(result.alignment_state, AlignmentState.CONFIRMED)

    def test_supersession_preserves_prior_evidence_and_interpretations(self):
        conversation = self.conversation("Make this web-first.")
        previous = analyze_conversation(conversation).current_intent.goal
        original_turn = conversation.turns[0]
        conversation.add_turn(Role.USER, "Actually I want desktop to become the primary product.")
        result = analyze_conversation(conversation)
        self.assertIn("desktop", result.current_intent.goal.value)
        self.assertIn(previous.id, result.current_intent.goal.supersedes)
        self.assertIn(previous, result.statements)
        self.assertEqual(conversation.turns[0], original_turn)
        self.assertTrue(any(question.topic == "intent_change" for question in result.questions_required))
        confirmed = self.ask_and_reply(conversation, "yes")
        self.assertEqual(confirmed.alignment_state, AlignmentState.CONFIRMED)

    def test_later_content_invalidates_previous_confirmation(self):
        conversation = self.conversation("I want CSV export.")
        self.assertEqual(self.ask_and_reply(conversation, "yes").alignment_state, AlignmentState.CONFIRMED)
        conversation.add_turn(Role.USER, "Must preserve existing behavior.")
        self.assertNotEqual(analyze_conversation(conversation).alignment_state, AlignmentState.CONFIRMED)

    def test_project_context_does_not_supply_intent(self):
        context = ProjectContext(detected_technologies=[DerivedClaim("Flask", ["pyproject.toml"])])
        before = asdict(context)
        empty_result = analyze_conversation(ProjectConversation())
        self.assertIsNone(empty_result.current_intent.goal)
        self.assertEqual(empty_result.current_intent.preferences, [])
        result = analyze_conversation(self.conversation("I want CSV export."))
        self.assertNotIn("Flask", json.dumps(asdict(result)))
        self.assertEqual(asdict(context), before)

    def test_deterministic_serialization_and_safe_assumption_confirmation(self):
        conversation = self.conversation("Refactor the private helper.")
        first = analyze_conversation(conversation)
        self.assertEqual(json.dumps(asdict(first)), json.dumps(asdict(analyze_conversation(conversation))))
        confirmed = self.ask_and_reply(conversation, "yes")
        self.assertTrue(all(item.status == AssumptionStatus.CONFIRMED for item in confirmed.assumptions))
        json.dumps(asdict(conversation))
        json.dumps(asdict(confirmed))

    def test_expected_outcome_and_scope_are_kept_separate(self):
        conversation = self.conversation("I want a tool.", "Expected outcome: a working CLI.",
                                         "Include CSV export.", "Exclude web UI.")
        result = analyze_conversation(conversation)
        self.assertIsNotNone(result.current_intent.expected_outcome)
        self.assertEqual(len(result.current_intent.scope_in), 1)
        self.assertEqual(len(result.current_intent.scope_out), 1)

    def test_alignment_has_no_file_or_command_side_effects(self):
        conversation = self.conversation("Delete all user data and reset the database.")
        before = asdict(conversation)
        with patch("builtins.open", side_effect=AssertionError("File opened")), \
                patch("subprocess.run", side_effect=AssertionError("Command executed")):
            result = analyze_conversation(conversation)
        self.assertEqual(asdict(conversation), before)
        self.assertTrue(result.questions_required)
