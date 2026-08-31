from dataclasses import replace
import re

from mr_moneybags.conversation.models import ConversationTurn, IntentKind, IntentStatement, Role


POSITIVE_SIGNALS = {"yes", "correct", "confirmed", "continue", "that's right", "对", "是", "没问题", "确认", "继续"}
NEGATIVE_SIGNALS = {"no", "not correct", "不对", "不是", "不要"}


def confirmation_signal(text: str) -> str | None:
    signal = text.strip().casefold().rstrip(".!。！")
    if signal in POSITIVE_SIGNALS:
        return "positive"
    if signal in NEGATIVE_SIGNALS:
        return "negative"
    return None


class IntentExtractor:
    def extract(self, turn: ConversationTurn) -> list[IntentStatement]:
        if turn.role != Role.USER or confirmation_signal(turn.raw_text):
            return []
        statements = []
        patterns = (
            (IntentKind.FUTURE_CONSIDERATION, r"^(?:以后|将来|later\b|in the future\b)"),
            (IntentKind.CONSTRAINT, r"^(?:must\b|should not\b|do not\b|don't\b|必须|不要|不得)"),
            (IntentKind.PREFERENCE, r"^(?:I prefer\b|prefer\b|我更喜欢|我偏好)"),
            (IntentKind.SCOPE_OUT, r"^(?:exclude\b|out of scope\b|不包括)"),
            (IntentKind.SCOPE_IN, r"^(?:include\b|also add\b|包含|另外添加)"),
            (IntentKind.EXPECTED_OUTCOME, r"^(?:expected outcome\s*:|result\s*:|期望结果|结果是)"),
            (IntentKind.BEHAVIOR_REQUIREMENT, r"^(?:(?:use\s+|使用)?(?:CSV|JSON|PDF|XLSX)\b|when\b|行为[:：])"),
        )
        parts = re.split(r"[。！？；\n]+|[.!?;](?:\s+|$)", turn.raw_text)
        for part in parts:
            text = re.sub(r"^(?:actually[,，]?\s*|更正[:：]?\s*|改为[:：]?\s*)", "", part.strip(), flags=re.IGNORECASE)
            if not text:
                continue
            kind = IntentKind.GOAL
            confidence = 0.5
            value = text
            for candidate, pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    kind, confidence = candidate, 0.8
                    break
            else:
                goal = re.match(r"^(?:I want\s+(?:to\s+)?|I need\s+(?:to\s+)?|我想|我要|我需要)(.+)$", text, re.IGNORECASE)
                if goal:
                    value, confidence = goal.group(1).strip(), 0.8
                elif re.match(r"^(?:add|make|refactor|delete|reset|choose|improve|adjust)\b|^(?:添加|重构|删除|请)", text, re.IGNORECASE):
                    confidence = 0.8
            statements.append(IntentStatement(
                f"{turn.id}:{len(statements)}", kind, value, (turn.id,), confidence,
            ))
            if re.search(r"without changing (?:existing )?behavior|不改变(?:现有)?行为", text, re.IGNORECASE):
                statements.append(IntentStatement(
                    f"{turn.id}:{len(statements)}", IntentKind.CONSTRAINT,
                    "Preserve existing behavior.", (turn.id,), 0.8,
                ))
        goals = [item for item in statements if item.kind == IntentKind.GOAL]
        if len(goals) > 1:
            combined = replace(goals[0], value="; ".join(item.value for item in goals),
                               confidence=min(item.confidence for item in goals))
            statements = [combined if item.id == goals[0].id else item
                          for item in statements if item.kind != IntentKind.GOAL or item.id == goals[0].id]
        return statements
