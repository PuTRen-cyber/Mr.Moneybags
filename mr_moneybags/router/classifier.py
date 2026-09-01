import re

from mr_moneybags.router.models import RouterDecision, TaskMode


class DecisionRouter:
    _VISION = re.compile(r'我想做一个|我想开发一个|我有一个想法|类似.+的产品')
    _CONCRETE_CHANGE = re.compile(r'修改|修复|增加|新增|删除|移除|重命名')
    _DOCUMENT_CHANGE = re.compile(r'README|说明文档|文档说明|\b[^\s]+\.(?:md|txt|rst)\b', re.IGNORECASE)
    _SPECIFIC_BUG = re.compile(r'修复.+(?:bug|错误|异常|无法|不能)', re.IGNORECASE)

    def classify(self, raw_input: str) -> RouterDecision:
        text = raw_input.strip()
        if self._VISION.search(text) and not self._CONCRETE_CHANGE.search(text):
            return RouterDecision(
                TaskMode.DISCOVERY_PATH,
                'product vision detected',
                'ask_clarifying_questions',
            )
        if self._DOCUMENT_CHANGE.search(text) or self._SPECIFIC_BUG.search(text):
            return RouterDecision(
                TaskMode.FAST_PATH,
                'specific modification request',
                'create_codex_brief',
            )
        return RouterDecision(
            TaskMode.STANDARD_PATH,
            'normal task preparation required',
            'create_codex_brief',
        )
