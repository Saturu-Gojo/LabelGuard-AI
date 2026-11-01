import json, os, re
_P = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rules", "ruleset.json")
RULES = json.load(open(_P))

def label(field): return RULES["field_labels"].get(field, field)
def criticality(field): return RULES["criticality"].get(field, "minor")

def classify_text(text, is_largest=False):
    for field, pat in RULES["field_classifier"]:
        if re.search(pat, text, re.I): return field
    return "product_name" if is_largest else "other_text"

def matches_value(expected, *candidates):
    """True if any candidate string matches the expected value (via alias table)."""
    keys = [expected.lower()] + RULES["value_aliases"].get(expected.lower(), [])
    blob = " ".join(str(c).lower() for c in candidates if c)
    return any(k in blob for k in keys)
