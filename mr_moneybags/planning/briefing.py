from mr_moneybags.planning.models import CurrentWorkUnit, StageBriefing


def build_briefing(title: str, unit: CurrentWorkUnit) -> StageBriefing:
    return StageBriefing(title, unit.objective.value, unit.why_now.value,
                        tuple(item.value for item in unit.scope_in), tuple(item.value for item in unit.scope_out),
                        tuple(item.value for item in unit.acceptance_criteria))
