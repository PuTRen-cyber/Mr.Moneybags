from mr_moneybags.planning.models import AgentTaskPackage
from mr_moneybags.safety.models import RiskLevel, SafetyDecision, SafetyStatus
from mr_moneybags.safety.rules import evaluate_rules


class SafetyGate:
    def evaluate(self, package: AgentTaskPackage) -> SafetyDecision:
        objective = package.objective.value.strip()
        if not objective or not any(character.isalnum() for character in objective):
            return SafetyDecision(SafetyStatus.BLOCK, RiskLevel.HIGH,
                                  ['Task objective is insufficient.'], ['missing_objective'])
        claims = (package.objective, *package.scope_in, *package.scope_out, *package.constraints,
                  *package.behavior_requirements, *package.acceptance_criteria)
        matches = evaluate_rules('\n'.join(claim.value for claim in claims).casefold())
        if not matches:
            return SafetyDecision(SafetyStatus.ALLOW, RiskLevel.LOW, [], [])
        risk = RiskLevel.HIGH if any(match[1] == RiskLevel.HIGH for match in matches) else RiskLevel.MEDIUM
        return SafetyDecision(SafetyStatus.REQUIRE_CONFIRMATION, risk,
                              [match[2] for match in matches], [match[0] for match in matches])
