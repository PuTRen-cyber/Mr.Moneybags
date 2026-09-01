from dataclasses import asdict
import json
import sys

from mr_moneybags.task import Task
from mr_moneybags.observation import observe_workspace
from mr_moneybags.context import build_project_context
from mr_moneybags.conversation.models import ProjectConversation, Role
from mr_moneybags.specification.builder import build_intent_specification
from mr_moneybags.specification.readiness import evaluate_readiness
from mr_moneybags.planning.planner import Planner
from mr_moneybags.reporter import build_codex_brief, build_human_report, format_codex_brief, format_human_report
from mr_moneybags.readiness import IntentReadinessClassifier, ReadinessStatus
from mr_moneybags.safety import SafetyGate
from mr_moneybags.semantic.interpreter import SemanticInterpreter, SemanticValidationError, interpret_conversation
from mr_moneybags.runtime import configured_interpreter


def _display_dict(value):
    return asdict(value, dict_factory=lambda items: {
        key: item for key, item in items
        if not (key in {'evidence', 'protected_target', 'implementation_delegation'} and item in (None, ()))
    })


def main(*, interpreter: SemanticInterpreter | None = None, debug: bool = False) -> int:
    print("Mr.Moneybags | JIA - Submit one task; no agent execution.")
    try:
        raw_input = input("Task: ")
    except EOFError:
        print()
        return 0

    try:
        task = Task(raw_input)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1

    if debug:
        print(json.dumps(asdict(task), ensure_ascii=False, indent=2))
    observation = observe_workspace()
    if debug:
        print("Workspace Observation:")
        print(json.dumps(asdict(observation), ensure_ascii=False, indent=2))
    context = build_project_context(observation)
    if debug:
        print("Project Context (Derived Understanding):")
        print(json.dumps(asdict(context), ensure_ascii=False, indent=2))
    conversation = ProjectConversation()
    conversation.add_turn(Role.USER, task.raw_input)
    try:
        if interpreter is None:
            interpreter = configured_interpreter()
        alignment = interpret_conversation(conversation, interpreter)
    except SemanticValidationError as error:
        print('Interpretation Failure:')
        failure = {'success': False, 'category': getattr(error, 'category', 'SemanticValidationError'),
                   'code': str(error), 'conversation': asdict(conversation)}
        if getattr(error, 'diagnostic', None) is not None:
            failure['diagnostic'] = error.diagnostic
        print(json.dumps(failure, ensure_ascii=False))
        print(f'Semantic interpretation rejected: {error}', file=sys.stderr)
        return 1
    if debug:
        print("Conversation / Intent Alignment:")
        print(json.dumps({"conversation": asdict(conversation),
                          "alignment": _display_dict(alignment)}, ensure_ascii=False, indent=2))
    intent_readiness = IntentReadinessClassifier().classify(task.raw_input, alignment.current_intent)
    if intent_readiness.status != ReadinessStatus.READY:
        print("Intent Readiness:")
        print(json.dumps(asdict(intent_readiness), ensure_ascii=False, indent=2))
        return 0
    specification = build_intent_specification(alignment)
    readiness = evaluate_readiness(specification)
    planning = Planner().plan(specification, context)
    if debug:
        print("Intent Specification / Readiness:")
        print(json.dumps({"specification": _display_dict(specification),
                          "readiness": _display_dict(readiness)}, ensure_ascii=False, indent=2))
        print("Planning:")
        print(json.dumps(_display_dict(planning), ensure_ascii=False, separators=(',', ':')))
        return 0
    package = planning.agent_task_package
    safety = SafetyGate().evaluate(package) if package is not None else None
    print(format_human_report(build_human_report(specification, safety)))
    if package is not None:
        print(format_codex_brief(build_codex_brief(package, safety)))
    return 0
