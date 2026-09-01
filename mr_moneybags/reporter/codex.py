from mr_moneybags.planning.models import AgentTaskPackage
from mr_moneybags.reporter.models import CodexBrief
from mr_moneybags.safety.models import SafetyDecision


def build_codex_brief(package: AgentTaskPackage,
                      safety: SafetyDecision | None = None) -> CodexBrief:
    objective = package.objective.value.strip() or 'Task objective is insufficient.'
    requirements = _values((*package.scope_in, *package.behavior_requirements))
    constraints = _values(package.constraints)
    constraints.extend(f'Do not include: {item.value}' for item in package.scope_out)
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
