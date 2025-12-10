# utils/explainers.py
from typing import Dict, Any, List

def build_explain_for_action(reflection: Dict[str,Any], decision: Dict[str,Any], patterns: List[Any], action: Dict[str,Any]) -> Dict[str,Any]:
    """
    Deterministic, auditable explain structure:
      - triggers: list of triggers
      - evidence: numeric indicators
      - applied_rule: text
    """
    triggers = []
    evidence = {}

    enriched = reflection.get('enriched', {}) or {}
    indicators = enriched.get('indicators', {}) or {}

    if enriched.get('regulatory_flag'):
        triggers.append('REGULATORY_FLAG')
        evidence['regulatory_flag'] = enriched.get('regulatory_flag')

    # severity in reflection might be 'low', 'medium', 'high' or numeric
    severity = reflection.get('severity')
    try:
        # try numeric compare
        severity_numeric = float(severity)
    except Exception:
        severity_numeric = None

    if severity_numeric is not None:
        if severity_numeric > 8:
            triggers.append('HIGH_VOLATILITY')
        evidence['severity'] = severity_numeric
    else:
        evidence['severity'] = severity

    # include simple indicators if present
    if 'volatility' in reflection:
        evidence['volatility'] = reflection.get('volatility')

    # patterns list may contain dicts or strings
    for p in (patterns or []):
        if isinstance(p, dict):
            triggers.append(p.get('name') or str(p))
        else:
            triggers.append(str(p))

    return {
        'triggers': list(dict.fromkeys(triggers)),
        'evidence': evidence,
        'applied_rule': action.get('reason'),
        'timestamp': None
    }
