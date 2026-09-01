import re

from mr_moneybags.safety.models import RiskLevel


DESTRUCTIVE_REASON = 'Potential destructive operation requires user confirmation.'
SENSITIVE_REASON = 'Sensitive system area requires confirmation before delegation.'
SCOPE_EXPANSION_REASON = 'Broad scope expansion requires user confirmation.'


def evaluate_rules(text):
    matches = []
    if _contains_destructive_operation(text):
        matches.append(('destructive_operations', RiskLevel.HIGH, DESTRUCTIVE_REASON))
    if re.search(r'\b(production environment|database|user data|authentication|permissions?|secrets?|payments?)\b', text):
        matches.append(('sensitive_areas', RiskLevel.HIGH, SENSITIVE_REASON))
    if re.search(r'\b(rewrite everything|complete refactor|redesign (?:the )?entire system|migrate all components)\b', text):
        matches.append(('scope_expansion', RiskLevel.MEDIUM, SCOPE_EXPANSION_REASON))
    return matches


def _contains_destructive_operation(text):
    without_safe_cleanup = re.sub(r'\bremove\s+(?:an?\s+)?unused imports?\b', '', text)
    return bool(re.search(r'\b(delete|remove|destroy|drop|clear|wipe)\b|\breset\s+(?:the\s+)?data\b',
                          without_safe_cleanup))
