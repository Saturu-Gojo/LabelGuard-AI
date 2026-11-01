"""Coordinator: optionally asks an LLM to rewrite explanations in reviewer-friendly language.
It may NOT change classification, severity, values or evidence — only 'explanation' text. Failure => deterministic text is kept."""
import json, os, re, urllib.request

def enrich(findings, contract):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key or not findings: return
    slim = [{"id": f["id"], "field": f["field_label"], "classification": f["classification"], "severity": f["severity"], "old": f["old_value"], "new": f["new_value"],
             "contract_note": f["contract_statement"], "sources": f["sources"]} for f in findings]
    prompt = ("You explain medical-device label inspection findings to QA reviewers. For each finding write ONE plain-language sentence (max 35 words). "
              "Do not change facts, values, classification or severity; do not make regulatory claims. Return JSON only: {\"LG-001\": \"...\", ...}\n" + json.dumps(slim))
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", method="POST",
        data=json.dumps({"model": os.environ.get("LLM_MODEL", "claude-sonnet-5-5"), "max_tokens": 1500, "messages": [{"role": "user", "content": prompt}]}).encode(),
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        txt = json.load(urllib.request.urlopen(req, timeout=40))["content"][0]["text"]
        d = json.loads(re.sub(r"```json|```", "", txt).strip())
        for f in findings:
            if isinstance(d.get(f["id"]), str): f["explanation_ai"] = d[f["id"]]
    except Exception:
        pass
