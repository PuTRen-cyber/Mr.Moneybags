from mr_moneybags.reporter.models import HumanReport
from mr_moneybags.safety.models import SafetyDecision, SafetyStatus
from mr_moneybags.specification.models import IntentSpecification
from mr_moneybags.decision_context.models import DecisionContext


def build_human_report(specification: IntentSpecification,
                       safety: SafetyDecision | None = None,
                       decision_context: DecisionContext | None = None) -> HumanReport:
    objective = decision_context.objective if decision_context is not None else specification.goal
    scope_in = decision_context.scope_in if decision_context is not None else specification.scope_in
    scope_out = decision_context.scope_out if decision_context is not None else specification.scope_out
    summary = objective.value.strip() if objective else ''
    status = specification.status.value
    if safety is not None and safety.status != SafetyStatus.ALLOW:
        status = safety.status.value
    return HumanReport(
        summary or 'Task objective is insufficient.',
        [item.value for item in scope_in],
        [item.value for item in scope_out],
        safety.risk_level.value if safety is not None else 'NOT_EVALUATED',
        status,
    )


def format_human_report(report: HumanReport) -> str:
    lines = ['Human Report:', f'Summary: {report.summary}', 'Scope In:']
    lines.extend(_items(report.scope_in))
    lines.append('Scope Out:')
    lines.extend(_items(report.scope_out))
    lines.extend((f'Risk: {report.risk}', f'Status: {report.status}'))
    return '\n'.join(lines)


def _items(values):
    return [f'- {value}' for value in values] or ['- None']
