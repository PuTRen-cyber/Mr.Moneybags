import unittest
from uuid import UUID

from mr_moneybags.task import Task


class TaskTest(unittest.TestCase):
    def test_preserves_input_and_trims_goal(self):
        raw_input = "  整理本周  工作计划\t "

        task = Task(raw_input)

        self.assertEqual(task.raw_input, raw_input)
        self.assertEqual(task.goal, "整理本周  工作计划")

    def test_generates_unique_uuid4_ids(self):
        first = Task("整理工作计划")
        second = Task("整理工作计划")

        self.assertEqual(UUID(first.id).version, 4)
        self.assertEqual(UUID(second.id).version, 4)
        self.assertNotEqual(first.id, second.id)

    def test_defaults_are_new_and_unspecified(self):
        task = Task("整理工作计划")

        self.assertEqual(task.status, "NEW")
        self.assertIsNone(task.expected_outcome)
        self.assertIsNone(task.constraints)
        self.assertIsNone(task.acceptance_criteria)

    def test_rejects_blank_input(self):
        for raw_input in ("", " \t "):
            with self.subTest(raw_input=raw_input):
                with self.assertRaisesRegex(ValueError, "must not be blank"):
                    Task(raw_input)
