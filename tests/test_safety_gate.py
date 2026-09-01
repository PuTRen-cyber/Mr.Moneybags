import unittest

from mr_moneybags.planning.models import AgentTaskPackage, ContextSummary, PlanningClaim
from mr_moneybags.safety import RiskLevel, SafetyGate, SafetyStatus


def claim(value):
    return PlanningClaim(value, ('turn-1',), 'user_intent')


def package(objective, *, scope=(), constraints=(), behavior=(), acceptance=()):
    return AgentTaskPackage(
        id='package-1', version=1, task_title='Task', objective=claim(objective), why=claim('Requested by user'),
        project_context_summary=ContextSummary((), (), ()), scope_in=tuple(map(claim, scope)), scope_out=(),
        constraints=tuple(map(claim, constraints)), behavior_requirements=tuple(map(claim, behavior)),
        acceptance_criteria=tuple(map(claim, acceptance)), verification_expectations=(), working_assumptions=(),
        user_decisions=(), allowed_agent_discretion=(), source_specification_id='spec-1',
        source_specification_version=1, source_stage_id='stage-1', source_work_unit_id='unit-1',
        provenance=('turn-1',),
    )


class SafetyGateTest(unittest.TestCase):
    def setUp(self):
        self.gate = SafetyGate()

    def test_normal_feature_is_allowed(self):
        decision = self.gate.evaluate(package('Add homework creation and viewing features.'))
        self.assertEqual(decision.status, SafetyStatus.ALLOW)
        self.assertEqual(decision.risk_level, RiskLevel.LOW)
        self.assertEqual(decision.reasons, [])
        self.assertEqual(decision.matched_rules, [])

    def test_delete_user_data_requires_confirmation(self):
        decision = self.gate.evaluate(package('Delete user data.'))
        self.assertEqual(decision.status, SafetyStatus.REQUIRE_CONFIRMATION)
        self.assertEqual(decision.risk_level, RiskLevel.HIGH)
        self.assertIn('destructive_operations', decision.matched_rules)
        self.assertIn('sensitive_areas', decision.matched_rules)

    def test_database_migration_requires_confirmation(self):
        decision = self.gate.evaluate(package('Migrate the database schema.'))
        self.assertEqual(decision.status, SafetyStatus.REQUIRE_CONFIRMATION)
        self.assertEqual(decision.risk_level, RiskLevel.HIGH)
        self.assertEqual(decision.matched_rules, ['sensitive_areas'])

    def test_complete_system_rewrite_requires_confirmation(self):
        decision = self.gate.evaluate(package('Rewrite everything in the application.'))
        self.assertEqual(decision.status, SafetyStatus.REQUIRE_CONFIRMATION)
        self.assertEqual(decision.risk_level, RiskLevel.MEDIUM)
        self.assertEqual(decision.matched_rules, ['scope_expansion'])

    def test_empty_objective_is_blocked(self):
        decision = self.gate.evaluate(package('   ', scope=('Add search.',)))
        self.assertEqual(decision.status, SafetyStatus.BLOCK)
        self.assertEqual(decision.risk_level, RiskLevel.HIGH)
        self.assertEqual(decision.reasons, ['Task objective is insufficient.'])
        self.assertEqual(decision.matched_rules, ['missing_objective'])

    def test_remove_unused_import_is_allowed(self):
        decision = self.gate.evaluate(package('Remove unused import.'))
        self.assertEqual(decision.status, SafetyStatus.ALLOW)
        self.assertEqual(decision.risk_level, RiskLevel.LOW)

    def test_production_word_without_environment_is_allowed(self):
        decision = self.gate.evaluate(package('Improve production build diagnostics.'))
        self.assertEqual(decision.status, SafetyStatus.ALLOW)
        self.assertEqual(decision.risk_level, RiskLevel.LOW)


if __name__ == '__main__':
    unittest.main()
