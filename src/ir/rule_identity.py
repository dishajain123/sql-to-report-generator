"""Keep rule references unique across independently generated synthesis sections."""
from typing import Any, Dict, List, Sequence


def unique_rule_ids(rules: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Copy rules, preserving unique supplied IDs and retaining repaired IDs as provenance.

    Reserve all supplied IDs before allocation so generated suffixes cannot steal
    a later rule's ID. Reapplying this operation is idempotent.
    """
    reserved = {str(rule.get("rule_id") or "").strip() for rule in rules}
    used = set()
    result = []
    for index, rule in enumerate(rules, 1):
        copy = dict(rule)
        original = str(rule.get("rule_id") or "").strip()
        identity = original
        if not identity or identity in used:
            base = original or "rule"
            suffix = index
            identity = f"{base}__{suffix}"
            while identity in reserved or identity in used:
                suffix += 1
                identity = f"{base}__{suffix}"
            if original:
                copy.setdefault("original_rule_id", original)
        copy["rule_id"] = identity
        used.add(identity)
        result.append(copy)
    return result
