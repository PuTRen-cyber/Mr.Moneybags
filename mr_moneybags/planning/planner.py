from dataclasses import asdict, replace
import json
import re
from uuid import NAMESPACE_URL, uuid5

from mr_moneybags.context.models import ProjectContext
from mr_moneybags.specification.models import IntentSpecification, SpecificationStatus
from mr_moneybags.specification.readiness import evaluate_readiness
from mr_moneybags.planning.briefing import build_briefing
from mr_moneybags.planning.package import build_package, summarize_context
from mr_moneybags.planning.models import (
    CurrentWorkUnit, PackageStatus, PlanningClaim, PlanningFailure, PlanningHorizon,
    PlanningMode, PlanningResult, PlanStage, PlanStatus, StageStatus,
)


class Planner:
    def plan(self, specification: IntentSpecification, project_context: ProjectContext,
             previous: PlanningResult | None = None) -> PlanningResult:
        spec = specification
        if spec.status != SpecificationStatus.READY:
            return PlanningResult(False, spec.id, blocking_reasons=(PlanningFailure(
                'SPECIFICATION_NOT_READY', f'Specification status is {spec.status}; return to intent readiness.', (spec.id,)),))
        readiness = evaluate_readiness(spec)
        if not readiness.ready:
            return PlanningResult(False, spec.id, blocking_reasons=tuple(
                PlanningFailure(item.category, item.description, (spec.id, *item.source_statement_ids, *item.source_turn_ids))
                for item in readiness.blocking_reasons))
        if previous and (not previous.success or spec.supersedes != previous.source_specification_id):
            return PlanningResult(False, spec.id, blocking_reasons=(PlanningFailure(
                'INVALID_PREDECESSOR', 'A replacement plan requires a superseding specification and a successful predecessor.', (spec.id,)),))
        version = previous.planning_horizon.version + 1 if previous else 1
        context = summarize_context(project_context)
        seed = json.dumps({'spec': asdict(spec), 'context': asdict(context), 'version': version,
                           'previous': previous.planning_horizon.id if previous else None}, sort_keys=True)

        def identifier(part):
            return str(uuid5(NAMESPACE_URL, seed + part))

        def intent(item):
            return PlanningClaim(item.value, (spec.id, item.id, *item.source_turn_ids), 'user_intent_interpretation')

        def rule(value, name, sources=()):
            return PlanningClaim(value, (spec.id, f'rule:{name}', *sources), 'planning_rule')

        objective = intent(spec.goal)
        scope_in = tuple(intent(item) for item in spec.scope_in) or (objective,)
        scope_out = tuple(intent(item) for item in spec.scope_out)
        constraints = tuple(intent(item) for item in spec.constraints)
        behavior = tuple(intent(item) for item in spec.behavior_requirements)
        preservation = [item for item in (spec.goal, *spec.constraints, *spec.behavior_requirements)
                        if re.search(r'preserv\w*.*behavior|without changing.*behavior|behavior.*unchanged|不改变.*行为|保持.*行为.*不变', item.value, re.IGNORECASE)
                        and not re.search(r'(?:do not|must not|should not|don\x27t|never)\s+preserv|不要保持|不要保留', item.value, re.IGNORECASE)]
        if preservation:
            scope_out += (rule('No redesign or new user-visible behavior beyond the stated change.',
                               'preserve_behavior_boundary', tuple(item.id for item in preservation)),)
        scope_out += tuple(rule(f'Deferred, not current scope: {item.value}', 'future_not_current', (item.id,))
                           for item in spec.future_considerations)
        why = rule('Deliver the currently agreed capability as one verifiable result before revisiting future directions.', 'meaningful_unit', (spec.goal.id,))
        stage = PlanStage(identifier('current'), spec.goal.value, objective, StageStatus.CURRENT,
                          scope_in, why, (spec.id, spec.goal.id, *(item.id for item in spec.scope_in)), True)
        future = []
        groups = [(item,) for item in spec.future_considerations[:2]]
        if len(spec.future_considerations) > 2:
            groups.append(spec.future_considerations[2:])
        for index, group in enumerate(groups):
            sources = tuple(item.id for item in group)
            direction = PlanningClaim('; '.join(item.value for item in group), (spec.id, *sources), 'future_consideration')
            future.append(PlanStage(identifier(f'future:{index}'), direction.value, direction, StageStatus.FUTURE,
                                    (), rule('Navigation only; reassess intent and project evidence before planning this direction.',
                                             'future_not_committed', sources), (spec.id, *sources), False))
        mode = PlanningMode.ROLLING if future else PlanningMode.FAST_PATH
        context_sources = tuple(dict.fromkeys(source for claim in context.claims for source in claim.source_ids))
        horizon = PlanningHorizon(identifier('horizon'), version, objective, mode, stage, tuple(future),
                                  spec.id, spec.version, context_sources,
                                  supersedes=previous.planning_horizon.id if previous else None)
        acceptance_sources = tuple(item for item in (spec.goal, spec.expected_outcome, *spec.scope_in,
                                                      *spec.constraints, *spec.behavior_requirements) if item)
        acceptance = tuple(rule(f'Demonstrate conformance to: {item.value}', 'intent_acceptance', (item.id,))
                           for item in acceptance_sources)
        verification = (rule('Provide relevant tests or checks for the stated acceptance criteria and report actual results; distinguish unrun checks.',
                             'verification_expectation', tuple(item.id for item in acceptance_sources)),)
        if project_context.test_commands:
            verification += (rule('Use the existing test approach where appropriate; context commands are unverified evidence, not execution instructions.',
                                  'existing_tests', tuple(source for item in project_context.test_commands for source in item.sources)),)
        discretion = tuple(rule(f'{choice}, within the current scope and constraints.', 'internal_discretion') for choice in (
            'Choose private helper names', 'Choose ordinary internal organization and refactoring details',
            'Choose the exact implementation sequence'))
        sources = tuple(dict.fromkeys((spec.id, *(item.id for item in acceptance_sources),
                                       *(item.id for item in spec.scope_out), *(item.id for item in spec.future_considerations),
                                       *(item.id for item in readiness.assumptions_in_effect), *spec.source_turn_ids)))
        unit = CurrentWorkUnit(identifier('unit'), version, objective, why, scope_in, scope_out, constraints, behavior,
                               acceptance, verification, discretion, readiness.assumptions_in_effect, spec.id, spec.version,
                               stage.id, sources, supersedes=previous.current_work_unit.id if previous else None)
        package = build_package(identifier('package'), stage.title, unit, spec, context,
                                previous.agent_task_package if previous else None)
        warnings = ('Deterministic grouping only: current scope stays together; only explicit future considerations form future stages.',)
        if len(spec.future_considerations) > 3:
            warnings += ('Further future considerations are grouped into one coarse direction without discarding their sources.',)
        return PlanningResult(True, spec.id, mode, horizon, unit, package, build_briefing(stage.title, unit), warnings=warnings)


def supersede_plan(old: PlanningResult, new: PlanningResult) -> PlanningResult:
    if not old.success or not new.success or new.planning_horizon.supersedes != old.planning_horizon.id:
        raise ValueError('Only a successful successor can supersede this plan.')
    return replace(old,
                   planning_horizon=replace(old.planning_horizon, status=PlanStatus.SUPERSEDED,
                                            current_stage=replace(old.planning_horizon.current_stage, status=StageStatus.SUPERSEDED),
                                            future_stages=tuple(replace(stage, status=StageStatus.SUPERSEDED)
                                                                for stage in old.planning_horizon.future_stages),
                                            superseded_by=new.planning_horizon.id),
                   current_work_unit=replace(old.current_work_unit, status=PlanStatus.SUPERSEDED,
                                             superseded_by=new.current_work_unit.id),
                   agent_task_package=replace(old.agent_task_package, status=PackageStatus.SUPERSEDED,
                                              superseded_by=new.agent_task_package.id))
