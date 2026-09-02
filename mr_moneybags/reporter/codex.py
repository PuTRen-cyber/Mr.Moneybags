from mr_moneybags.planning.models import AgentTaskPackage
from mr_moneybags.decision_context.models import DecisionContext
from mr_moneybags.reporter.models import CodexBrief
from mr_moneybags.safety.models import SafetyDecision


def build_codex_brief(package: AgentTaskPackage,
                      safety: SafetyDecision | None = None,
                      decision_context: DecisionContext | None = None) -> CodexBrief:
    objective_claim = decision_context.objective if decision_context is not None else package.objective
    objective = objective_claim.value.strip() if objective_claim else ''
    objective = objective or 'Task objective is insufficient.'
    if decision_context is None:
        scope_in = package.scope_in
        requirements = _values((*scope_in, *package.behavior_requirements))
        constraints = _values(package.constraints)
        scope_out = package.scope_out
    else:
        context_scope_out = tuple(decision_context.scope_out)
        context_ids = {item.id for item in context_scope_out}
        requirements = _values(decision_context.scope_in)
        constraints = _values(item for item in package.constraints
                              if not context_ids.intersection(item.source_ids))
        scope_out = context_scope_out
    constraints.extend(f'Do not include: {item.value}' for item in scope_out)
    return CodexBrief(
        package.task_title,
        objective,
        requirements,
        list(dict.fromkeys(constraints)),
        _values(package.acceptance_criteria),
        _values(package.allowed_agent_discretion),
        _values(package.verification_expectations),
        list(safety.reasons) if safety is not None else [],
    )


def format_codex_brief(brief: CodexBrief) -> str:
    lines = ['Codex Brief:', f'Task: {brief.task_title}', f'Objective: {brief.objective}']
    for title, values in (
        ('Requirements', brief.requirements),
        ('Constraints', brief.constraints),
        ('Acceptance Criteria', brief.acceptance_criteria),
        ('Implementation Guidance', brief.implementation_guidance),
        ('Verification', brief.verification),
        ('Risk Notes', brief.risk_notes),
    ):
        lines.append(f'{title}:')
        lines.extend([f'- {value}' for value in values] or ['- None'])
    return '\n'.join(lines)


def _values(claims):
    return list(dict.fromkeys(item.value for item in claims))
