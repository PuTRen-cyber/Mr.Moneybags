from mr_moneybags.reporter.models import HumanReport
from mr_moneybags.safety.models import SafetyDecision, SafetyStatus
from mr_moneybags.specification.models import IntentSpecification


def build_human_report(specification: IntentSpecification,
                       safety: SafetyDecision | None = None) -> HumanReport:
    summary = specification.goal.value.strip() if specification.goal else ''
    status = specification.status.value
    if safety is not None and safety.status != SafetyStatus.ALLOW:
        status = safety.status.value
    return HumanReport(
        summary or 'Task objective is insufficient.',
        [item.value for item in specification.scope_in],
        [item.value for item in specification.scope_out],
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
