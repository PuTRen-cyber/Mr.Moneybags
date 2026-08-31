from mr_moneybags.context.models import ProjectContext
from mr_moneybags.specification.models import IntentSpecification
from mr_moneybags.planning.models import (
    AgentTaskPackage, ContextSource, ContextSummary, CurrentWorkUnit, PlanningClaim,
)


def summarize_context(context: ProjectContext) -> ContextSummary:
    claims = []
    for name in ('project_name', 'project_summary', 'detected_technologies', 'entry_points',
                 'test_commands', 'architecture_notes'):
        value = getattr(context, name)
        for item in value if isinstance(value, list) else (() if value is None else (value,)):
            claims.append(PlanningClaim(f'{name}: {item.value}', tuple(item.sources), 'project_evidence'))
    paths = {source for claim in claims for source in claim.source_ids}
    warnings = tuple(context.warnings) + tuple(f'Context conflict: {item.field}: {item.reason}' for item in context.conflicts)
    return ContextSummary(tuple(claims), tuple(ContextSource(s.path, s.sha256, s.size_bytes)
                                               for s in context.sources if s.path in paths), warnings)


def build_package(identifier: str, title: str, unit: CurrentWorkUnit, spec: IntentSpecification,
                  context: ContextSummary, previous: AgentTaskPackage | None = None) -> AgentTaskPackage:
    provenance = tuple(dict.fromkeys((*unit.source_ids, spec.id,
                                     *(source for claim in context.claims for source in claim.source_ids))))
    return AgentTaskPackage(
        id=identifier, version=unit.version, task_title=title, objective=unit.objective, why=unit.why_now,
        project_context_summary=context, scope_in=unit.scope_in, scope_out=unit.scope_out,
        constraints=unit.constraints, behavior_requirements=unit.behavior_requirements,
        acceptance_criteria=unit.acceptance_criteria, verification_expectations=unit.verification_expectations,
        working_assumptions=unit.known_assumptions, user_decisions=spec.user_decisions,
        allowed_agent_discretion=unit.allowed_agent_discretion,
        source_specification_id=spec.id, source_specification_version=spec.version,
        source_stage_id=unit.source_stage_id, source_work_unit_id=unit.id, provenance=provenance,
        supersedes=previous.id if previous else None,
    )
