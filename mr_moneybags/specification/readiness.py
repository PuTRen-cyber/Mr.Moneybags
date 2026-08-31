import re

from mr_moneybags.conversation.alignment import requires_user_confirmation
from mr_moneybags.conversation.models import AmbiguityStatus, AssumptionStatus, Materiality, QuestionRequest
from mr_moneybags.specification.models import (
    BlockingCategory, BlockingReason, IntentSpecification, ReadinessResult,
    ReadinessStatus, SpecificationStatus,
)


def _conflicts(spec: IntentSpecification) -> list[BlockingReason]:
    reasons = []
    actionable = tuple(item for item in (spec.goal, *spec.scope_in, *spec.behavior_requirements) if item)
    preserve = r'(?:do not|should not|must not|never|don\x27t) change|preserve|keep.*unchanged|不改变|不要改变|保持.*不变'
    change = r'\b(?:replace|change|redesign)\b|替换|改变|重做'
    for constraint in spec.constraints:
        if not re.search(preserve, constraint.value, re.IGNORECASE):
            continue
        for claim in actionable:
            if (re.search(r'authentication|认证|登录', constraint.value, re.IGNORECASE)
                    and re.search(r'authentication|认证|登录', claim.value, re.IGNORECASE)
                    and re.search(r'\b(?:behavior|flow|workflow)\b|行为|流程', claim.value, re.IGNORECASE)
                    and re.search(change, claim.value, re.IGNORECASE)
                    and not re.search(preserve, claim.value, re.IGNORECASE)):
                reasons.append(BlockingReason(
                    BlockingCategory.CONFLICTING_USER_INTENT,
                    'An active authentication-preservation constraint conflicts with the requested change.',
                    tuple(dict.fromkeys((*constraint.source_turn_ids, *claim.source_turn_ids))),
                    (constraint.id, claim.id),
                ))
    def scope_value(value: str) -> str:
        return re.sub(r'^(?:include\b|exclude\b|out of scope\b|包含|不包括)\s*[:：]?\s*',
                      '', value.strip(), flags=re.IGNORECASE).rstrip('.。').casefold()

    for included in spec.scope_in:
        for excluded in spec.scope_out:
            if scope_value(included.value) == scope_value(excluded.value):
                reasons.append(BlockingReason(
                    BlockingCategory.UNRESOLVED_SCOPE, 'The same scope item is both included and excluded.',
                    tuple(dict.fromkeys((*included.source_turn_ids, *excluded.source_turn_ids))),
                    (included.id, excluded.id),
                ))
    return reasons


def evaluate_readiness(spec: IntentSpecification) -> ReadinessResult:
    if spec.status == SpecificationStatus.SUPERSEDED:
        raise ValueError('Evaluate the current specification, not a superseded snapshot.')
    reasons = []
    goal = spec.goal.value.strip() if spec.goal else ''
    if (not any(char.isalnum() for char in goal)
            or goal.casefold().rstrip('.!。！') in {'something', 'do it', 'whatever', '随便', '做点什么'}):
        reasons.append(BlockingReason(BlockingCategory.INSUFFICIENT_GOAL,
                                      'A meaningful intended outcome is required.',
                                      spec.goal.source_turn_ids if spec.goal else (),
                                      (spec.goal.id,) if spec.goal else ()))
    unknowns = []
    blocked_ids = set()
    for item in spec.ambiguities:
        if item.status == AmbiguityStatus.RESOLVED:
            if item.topic != 'destructive_action' or spec.confirmation_turn_ids:
                continue
        high_unresolved = item.materiality == Materiality.HIGH and item.status != AmbiguityStatus.RESOLVED
        missing_confirmation = item.topic == 'destructive_action' and not spec.confirmation_turn_ids
        if requires_user_confirmation(item) or high_unresolved or missing_confirmation:
            if item.topic in {'intent_change', 'project_context_conflict'}:
                category = BlockingCategory.CONFLICTING_USER_INTENT
            elif item.topic in {'destructive_action', 'confirmation_rejected', 'confirmation_unclear'}:
                category = BlockingCategory.MISSING_REQUIRED_CONFIRMATION
            elif item.materiality == Materiality.HIGH:
                category = BlockingCategory.HIGH_IMPACT_UNRESOLVED_DECISION
            else:
                category = BlockingCategory.UNRESOLVED_MATERIAL_AMBIGUITY
            reasons.append(BlockingReason(category, item.description, item.source_turn_ids, ambiguity_id=item.id))
            blocked_ids.add(item.id)
        else:
            unknowns.append(QuestionRequest(item.topic, item.description, item.id, item.materiality))
    by_id = {item.id: item for item in spec.ambiguities}
    for question in spec.required_questions:
        item = by_id.get(question.ambiguity_id)
        if question.ambiguity_id in blocked_ids or (item and item.status == AmbiguityStatus.RESOLVED):
            continue
        reasons.append(BlockingReason(BlockingCategory.MISSING_REQUIRED_CONFIRMATION, question.reason,
                                      item.source_turn_ids if item else spec.source_turn_ids,
                                      ambiguity_id=question.ambiguity_id))
        blocked_ids.add(question.ambiguity_id)
    assumptions = []
    blocked_assumptions = {item.safe_assumption.id for item in spec.ambiguities
                           if item.id in blocked_ids and item.safe_assumption is not None}
    for item in spec.working_assumptions:
        if item.status not in {AssumptionStatus.ACTIVE, AssumptionStatus.CONFIRMED} or item.id in blocked_assumptions:
            continue
        if item.materiality == Materiality.LOW and item.reversible:
            assumptions.append(item)
        else:
            reasons.append(BlockingReason(BlockingCategory.HIGH_IMPACT_UNRESOLVED_DECISION,
                                          'This assumption is not a low-impact reversible working choice.',
                                          item.source_turn_ids, assumption_id=item.id))
    reasons.extend(_conflicts(spec))
    unknowns = [item for item in unknowns if item.ambiguity_id not in blocked_ids]
    return ReadinessResult(not reasons, ReadinessStatus.NOT_READY if reasons else ReadinessStatus.READY,
                           tuple(reasons), tuple(unknowns), tuple(assumptions), spec.source_intent_version, spec.id)
