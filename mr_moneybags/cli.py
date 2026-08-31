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
from mr_moneybags.semantic.interpreter import SemanticInterpreter, SemanticValidationError, interpret_conversation


def _display_dict(value):
    return asdict(value, dict_factory=lambda items: {
        key: item for key, item in items
        if not (key in {'evidence', 'protected_target', 'implementation_delegation'} and item in (None, ()))
    })


def main(*, interpreter: SemanticInterpreter | None = None) -> int:
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

    print(json.dumps(asdict(task), ensure_ascii=False, indent=2))
    observation = observe_workspace()
    print("Workspace Observation:")
    print(json.dumps(asdict(observation), ensure_ascii=False, indent=2))
    print("Project Context (Derived Understanding):")
    context = build_project_context(observation)
    print(json.dumps(asdict(context), ensure_ascii=False, indent=2))
    conversation = ProjectConversation()
    conversation.add_turn(Role.USER, task.raw_input)
    try:
        alignment = interpret_conversation(conversation, interpreter)
    except SemanticValidationError as error:
        print('Interpretation Failure:')
        print(json.dumps({'success': False, 'code': str(error), 'conversation': asdict(conversation)}, ensure_ascii=False))
        print(f'Semantic interpretation rejected: {error}', file=sys.stderr)
        return 1
    print("Conversation / Intent Alignment:")
    print(json.dumps({"conversation": asdict(conversation),
                      "alignment": _display_dict(alignment)}, ensure_ascii=False, indent=2))
    specification = build_intent_specification(alignment)
    print("Intent Specification / Readiness:")
    print(json.dumps({"specification": _display_dict(specification),
                      "readiness": _display_dict(evaluate_readiness(specification))}, ensure_ascii=False, indent=2))
    print("Planning:")
    print(json.dumps(_display_dict(Planner().plan(specification, context)), ensure_ascii=False, separators=(',', ':')))
    return 0
