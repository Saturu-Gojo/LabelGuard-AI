"""Change Contract generator. LLM (if ANTHROPIC_API_KEY set) with deterministic fallback.
The contract is ALWAYS a draft until a human confirms it."""
import json, os, re, urllib.request
from . import ruleset

FIELD_SYNONYMS = {
    "sterilization_symbol": ["sterilization symbol", "sterile symbol", "sterilization method", "sterilisation method", "sterilization", "sterilisation"],
    "sterilization_statement": ["sterilization statement", "sterilization text", "sterilization method", "sterilization", "sterilisation"],
    "udi": ["udi", "unique device identif", "barcode"],
    "product_id": ["product identification", "product identifier", "product id", "ref number", "catalog"],
    "product_name": ["product name"],
    "manufacturer_details": ["manufacturer", "manufacturing details"],
    "safety_warnings": ["safety warning", "warnings", "warning", "caution"],
    "logo": ["logo"],
}
METHODS = {"radiation": ["radiation", "irradiation", "gamma", "e-beam"], "eo": ["eo", "ethylene oxide"], "steam": ["steam", "autoclave"]}
PROTECT_CUES = r"(keep|keeping|unchanged|must remain|remain|do not change|don't change|without changing|retain|preserve|leave)"

def _fields_in(text):
    t = text.lower(); found = []
    for f, syns in FIELD_SYNONYMS.items():
        if any(s in t for s in syns): found.append(f)
    return found

def heuristic_contract(change_request, change_id="CHG-001", reason=""):
    allowed, protected = [], []
    for sent in re.split(r"(?<=[.;!?])\s+", change_request.strip()):
        fields = _fields_in(sent)
        if not fields: continue
        if re.search(PROTECT_CUES, sent, re.I) and re.search(r"unchanged|remain|retain|preserve|keep|leave", sent, re.I):
            protected += [f for f in fields if f not in protected]
        else:
            m = re.search(r"\bto\s+([A-Za-z\- ]+?)(?:[.,;]|$)", sent); target = None
            if m:
                tgt = m.group(1).strip().lower()
                for k, al in METHODS.items():
                    if tgt == k or tgt in al: target = k
            for f in fields:
                if f in ("sterilization_symbol", "sterilization_statement") and not target: 
                    allowed.append({"field": f, "expected_value": None}); continue
                if f in ("sterilization_symbol", "sterilization_statement"):
                    allowed.append({"field": f, "expected_value": target})
                else: allowed.append({"field": f, "expected_value": None})
    seen, uniq = set(), []
    for a in allowed:
        if a["field"] not in seen: seen.add(a["field"]); uniq.append(a)
    protected = [p for p in protected if p not in seen]
    return {"change_id": change_id, "reason": reason, "allowed_changes": uniq, "protected_fields": protected,
            "requires_human_review": True, "generated_by": "heuristic", "status": "DRAFT"}

def llm_contract(change_request, change_id, reason):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key: return None
    fields = list(FIELD_SYNONYMS)
    prompt = (f"Convert this label change request into JSON only (no prose, no code fences).\nSchema: "
              '{"allowed_changes":[{"field":str,"expected_value":str|null}],"protected_fields":[str]}\n'
              f"Valid fields: {fields}. expected_value for sterilization fields must be one of eo|radiation|steam or null.\n"
              f"Only list a field as protected if the request says it must stay unchanged.\nRequest: {change_request}")
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", method="POST",
        data=json.dumps({"model": os.environ.get("LLM_MODEL", "claude-sonnet-5-5"), "max_tokens": 800, "messages": [{"role": "user", "content": prompt}]}).encode(),
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        txt = json.load(urllib.request.urlopen(req, timeout=30))["content"][0]["text"]
        d = json.loads(re.sub(r"```json|```", "", txt).strip())
        al = [a for a in d["allowed_changes"] if a["field"] in FIELD_SYNONYMS]
        pr = [p for p in d["protected_fields"] if p in FIELD_SYNONYMS]
        return {"change_id": change_id, "reason": reason, "allowed_changes": al, "protected_fields": pr,
                "requires_human_review": True, "generated_by": "llm", "status": "DRAFT"}
    except Exception:
        return None

def generate(change_request, change_id="CHG-001", reason=""):
    return llm_contract(change_request, change_id, reason) or heuristic_contract(change_request, change_id, reason)
