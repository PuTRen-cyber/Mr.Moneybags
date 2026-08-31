from dataclasses import replace
import re

from mr_moneybags.conversation.models import (
    Ambiguity, AmbiguityStatus, Assumption, DecisionOwner,
    IntentKind, IntentStatement, Materiality,
)


def classify_decision(topic: str) -> DecisionOwner:
    if topic in {"export_format", "visual_direction", "destructive_action", "intent_change", "confirmation_rejected", "confirmation_unclear", "behavior_choice"}:
        return DecisionOwner.USER
    if topic in {"helper_naming", "internal_organization", "internal_refactor", "implementation_style"}:
        return DecisionOwner.JIA_AGENT
    return DecisionOwner.SHARED


class AmbiguityDetector:
    def detect(self, statements: list[IntentStatement]) -> list[Ambiguity]:
        actionable = [item for item in statements if item.kind in {
            IntentKind.GOAL, IntentKind.SCOPE_IN, IntentKind.BEHAVIOR_REQUIREMENT,
        }]
        if not actionable:
            return []
        text = "\n".join(item.value for item in actionable)
        sources = tuple(dict.fromkeys(source for item in actionable for source in item.source_turn_ids))
        ambiguities = []

        def add(topic: str, description: str, candidates: tuple[str, ...], materiality: Materiality) -> Ambiguity:
            item = Ambiguity(f"{sources[0]}:{topic}", topic, description, candidates,
                             sources, classify_decision(topic), materiality)
            ambiguities.append(item)
            return item

        if re.search(r"\bexport\b|导出", text, re.IGNORECASE):
            formats = tuple(dict.fromkeys(re.findall(r"\b(?:CSV|JSON|PDF|XLSX)\b", text.upper())))
            item = add("export_format", "Export format is a user-visible choice.",
                       formats or ("CSV", "JSON", "PDF", "XLSX"), Materiality.MEDIUM)
            if formats and not re.search(r"\bor\b|或者|还是", text, re.IGNORECASE):
                ambiguities[-1] = replace(item, status=AmbiguityStatus.RESOLVED, resolution=", ".join(formats))

        if (re.search(r"nicer|prettier|美化|更好看", text, re.IGNORECASE)
                and re.search(r"login|page|\bUI\b|登录|页面|界面", text, re.IGNORECASE)):
            item = add("visual_direction", "The desired visual direction is unspecified.",
                       ("subtle visual cleanup", "different visual style"), Materiality.MEDIUM)
            preferences = [item for item in statements if item.kind == IntentKind.PREFERENCE
                           and re.search(r"visual|style|interface|layout|minimal|color|简洁|极简|风格|配色|界面|布局", item.value, re.IGNORECASE)]
            if preferences:
                ambiguities[-1] = replace(item, status=AmbiguityStatus.RESOLVED,
                                          resolution=preferences[-1].value,
                                          source_turn_ids=tuple(dict.fromkeys((*sources, *preferences[-1].source_turn_ids))))

        destructive = re.search(r"\b(?:delete|wipe|remove)\b.{0,40}\b(?:data|records|database)\b|\breset\b.{0,25}\b(?:database|db)\b|删除.{0,15}数据|重置.{0,10}数据库", text, re.IGNORECASE)
        negated = re.search(r"\b(?:do not|don't|never|avoid|without)\b.{0,25}\b(?:delete|wipe|remove|reset)\b|不要删除|不重置", text, re.IGNORECASE)
        if destructive and not negated:
            add("destructive_action", "Explicit acknowledgment is required for the requested destructive data operation.",
                ("perform the requested data operation", "do not perform it"), Materiality.HIGH)

        internal = re.search(r"refactor|helper.*nam|private helper|variable nam|internal.*organiz|重构|函数命名|变量命名|内部结构", text, re.IGNORECASE)
        behavior_changes = [item for item in statements if item.kind != IntentKind.FUTURE_CONSIDERATION
                            and re.search(r"(?:do not|don't) preserve.{0,20}behavior|\bchange\b.{0,20}\bbehavior\b|改变.{0,10}行为|不要保留.{0,10}行为", item.value, re.IGNORECASE)
                            and not re.search(r"(?:do not|should not|don't) change|without changing|不要改变|不改变", item.value, re.IGNORECASE)]
        if internal and behavior_changes:
            item = add("behavior_choice", "The requested behavior change cannot use an internal-only preservation assumption.",
                       (), Materiality.MEDIUM)
            ambiguities[-1] = replace(item, source_turn_ids=tuple(dict.fromkeys(
                (*sources, *(source for statement in behavior_changes for source in statement.source_turn_ids)))))
        elif internal:
            item = add("internal_refactor", "Private naming and internal organization are implementation-owned.",
                       (), Materiality.LOW)
            assumption = Assumption(
                f"{item.id}:assumption", "Choose private names and internal organization while preserving observable behavior.",
                "An internal-only change is reversible and does not select new product behavior.",
                sources, Materiality.LOW, True,
            )
            ambiguities[-1] = replace(item, safe_assumption=assumption)

        if re.search(r"(?:performance|security|cost|portability).{0,25}(?:\bvs\b|\bversus\b|\bor\b)|性能.{0,10}权衡|安全.{0,10}权衡", text, re.IGNORECASE):
            add("technical_tradeoff", "The technical tradeoff may materially affect product behavior or constraints.",
                (), Materiality.HIGH)
        return ambiguities
