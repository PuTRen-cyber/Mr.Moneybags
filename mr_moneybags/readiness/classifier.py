import re

from mr_moneybags.conversation.models import CurrentIntent
from mr_moneybags.readiness.models import IntentReadinessResult, ReadinessStatus


class IntentReadinessClassifier:
    _VISION = re.compile(r'我想做一个|我想开发一个|我有一个想法|类似.+的产品')
    _DETAIL = re.compile(r'可以|能够|支持|只修改|不修改|必须|不得|要求|无法|不能|启动说明|启动命令|测试命令|以后再考虑|验收')
    _VAGUE_CHANGE = re.compile(r'^(?:请|帮我)?(?:优化|改善|提升).+|^(?:请|帮我)?增加(?:数据分析|分析|统计)功能[。.!]?$')

    def classify(self, raw_input: str, intent: CurrentIntent) -> IntentReadinessResult:
        text = raw_input.strip()
        if intent.goal is None or not intent.goal.value.strip():
            return self._clarification('The request does not contain a concrete objective.')
        if self._VISION.search(text) and not self._DETAIL.search(text):
            return IntentReadinessResult(
                ReadinessStatus.DISCOVERY_REQUIRED,
                'User expressed a product vision rather than an executable task.',
                ['target users', 'core problem', 'first version scope'],
                ['这个软件主要帮助哪类大学生？', '你希望第一版解决什么学习问题？'],
            )
        if self._VAGUE_CHANGE.search(text) and not self._DETAIL.search(text):
            return self._clarification('The request has a concrete direction but lacks execution details.')
        return IntentReadinessResult(
            ReadinessStatus.READY,
            'Request is concrete enough to prepare a task package.',
        )

    @staticmethod
    def _clarification(reason: str) -> IntentReadinessResult:
        return IntentReadinessResult(
            ReadinessStatus.NEEDS_CLARIFICATION,
            reason,
            ['scope', 'expected behavior', 'acceptance criteria'],
            ['具体需要改变哪些行为？', '完成后应满足哪些验收条件？'],
        )
