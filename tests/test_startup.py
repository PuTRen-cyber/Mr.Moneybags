from pathlib import Path
import json
import os
import subprocess
import sys
import unittest


class StartupTest(unittest.TestCase):
    def run_cli(self, user_input):
        return subprocess.run(
            [sys.executable, "-m", "mr_moneybags"],
            cwd=Path(__file__).resolve().parents[1],
            input=user_input,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8", "MR_MONEYBAGS_SEMANTIC_MODE": "deterministic"},
            timeout=10,
        )

    def test_module_creates_one_task_and_exits(self):
        raw_input = "  请整理本周工作计划  "
        result = self.run_cli(raw_input + "\n不要处理第二条任务\n")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Mr.Moneybags", result.stdout)
        self.assertIn("JIA", result.stdout)
        task_output, observation_output = result.stdout.split("Workspace Observation:\n", 1)
        observation_output, context_output = observation_output.split("Project Context (Derived Understanding):\n", 1)
        context_output, alignment_output = context_output.split("Conversation / Intent Alignment:\n", 1)
        alignment_output, specification_output = alignment_output.split("Intent Specification / Readiness:\n", 1)
        specification_output, planning_output = specification_output.split("Planning:\n", 1)
        task = json.loads(task_output[task_output.index("{"):])
        observation = json.loads(observation_output)
        context = json.loads(context_output)
        alignment = json.loads(alignment_output)
        specification = json.loads(specification_output)
        planning = json.loads(planning_output)
        self.assertEqual(planning['source_specification_id'], specification['specification']['id'])
        self.assertIn('stage_briefing', planning)
        self.assertEqual(specification["specification"]["source_intent_version"],
                         alignment["alignment"]["current_intent"]["revision"])
        self.assertEqual(specification["readiness"]["specification_id"], specification["specification"]["id"])
        self.assertEqual(specification["specification"]["trust_level"], 'Derived Intent Specification / Interpretation')
        self.assertEqual(alignment["conversation"]["turns"][0]["raw_text"], raw_input)
        self.assertEqual(alignment["alignment"]["trust_level"], "Derived Intent / Interpretation")
        self.assertEqual(context["trust_level"], "Derived Context / Interpretation")
        self.assertNotIn("working_tree_clean", context)
        self.assertNotIn("project_name", observation)
        self.assertEqual(observation["trust_level"], "Tier 0 — Direct Evidence")
        self.assertEqual(Path(observation["cwd"]), Path(__file__).resolve().parents[1])
        self.assertIsInstance(observation["files"], list)
        self.assertEqual(
            set(task),
            {"id", "raw_input", "goal", "expected_outcome", "constraints",
             "acceptance_criteria", "status"},
        )
        self.assertTrue(task["id"])
        self.assertEqual(task["raw_input"], raw_input)
        self.assertEqual(task["goal"], raw_input.strip())
        self.assertEqual(task["status"], "NEW")
        self.assertIsNone(task["expected_outcome"])
        self.assertIsNone(task["constraints"])
        self.assertIsNone(task["acceptance_criteria"])
        self.assertEqual(result.stderr, "")

    def test_blank_input_exits_without_creating_task(self):
        result = self.run_cli("  \t\n")

        self.assertEqual(result.returncode, 1)
        self.assertIn("Task input must not be blank.", result.stderr)
        self.assertNotIn("{", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_end_of_input_exits_normally(self):
        result = self.run_cli("")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("{", result.stdout)
        self.assertEqual(result.stderr, "")
