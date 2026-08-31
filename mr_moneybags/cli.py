from dataclasses import asdict
import json
import sys

from mr_moneybags.task import Task
from mr_moneybags.observation import observe_workspace
from mr_moneybags.context import build_project_context
from mr_moneybags.conversation.alignment import analyze_conversation
from mr_moneybags.conversation.models import ProjectConversation, Role


def main() -> int:
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
    print(json.dumps(asdict(build_project_context(observation)), ensure_ascii=False, indent=2))
    conversation = ProjectConversation()
    conversation.add_turn(Role.USER, task.raw_input)
    print("Conversation / Intent Alignment:")
    print(json.dumps({"conversation": asdict(conversation),
                      "alignment": asdict(analyze_conversation(conversation))}, ensure_ascii=False, indent=2))
    return 0
