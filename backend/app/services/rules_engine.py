"""Intent-aware rules engine (deterministic). Classification (EXPECTED/UNEXPECTED/REQUIRES_REVIEW) is separate from severity."""
from . import ruleset, barcode_validator
SEV_ORDER = {"critical": 0, "major": 1, "minor": 2, "informational": 3}
CLS_ORDER = {"UNEXPECTED": 0, "REQUIRES_REVIEW": 1, "EXPECTED": 2}

def _merge(changes):
    groups = {}
    for c in changes:
        key = (c["field"], c["change_type"] if c["field"] != "udi" else "udi")
        groups.setdefault(key, []).append(c)
    return list(groups.values())

def _evidence(c):
    return {"source": c["sources"][0], "page": c["page"], "bbox_old": c["bbox_old"], "bbox_new": c["bbox_new"], "old": c["old"], "new": c["new"], **({"detail": c["detail"]} if c.get("detail") else {})}

def _fmt(v): return "—" if v in (None, "") else str(v)

def _classify(field, ctype, new_vals, contract):
    allowed = {a["field"]: a for a in contract["allowed_changes"]}
    if field in allowed:
        exp = allowed[field].get("expected_value")
        if ctype == "removed": return "UNEXPECTED", f"Requested change for this field expects a replacement, but the element was removed."
        if exp and not ruleset.matches_value(exp, *new_vals):
            return "UNEXPECTED", f"Field may change, but the new value does not match the requested value '{exp}'."
        return "EXPECTED", f"Change request {contract['change_id']} allows this field to change" + (f" to '{exp}'." if exp else ".")
    if field in contract["protected_fields"]:
        return "UNEXPECTED", f"Change request {contract['change_id']} explicitly protects this field."
    return "REQUIRES_REVIEW", "This field is not covered by the change request; insufficient evidence to accept the change."

ACTIONS = {
    "UNEXPECTED": "Verify the correct value against the source of truth and regenerate the candidate label if the change was not intended.",
    "REQUIRES_REVIEW": "Reviewer to inspect the highlighted region and confirm whether the change is acceptable; document the rationale.",
    "EXPECTED": "No action required; confirm that the new value is correct for the target market.",
}

def analyze(changes, contract, old_pages, new_pages, visual_regions):
    findings, checks = [], []
    changes = [c for c in changes if c["field"] != "ignored"]
    changed_fields = set()
    for grp in _merge(changes):
        main = next((c for c in grp if "text" in c["sources"] or "symbol" in c["sources"]), grp[0])
        field, ctype = main["field"], main["change_type"]; changed_fields.add(field)
        new_vals = [c["new"] for c in grp]
        cls, why = _classify(field, ctype, new_vals, contract)
        sev = "informational" if cls == "EXPECTED" else ruleset.criticality(field)
        label = ruleset.label(field)
        refs = []
        if field in contract["protected_fields"]: refs.append("LG-CONTRACT-PROTECTED")
        if field in [a["field"] for a in contract["allowed_changes"]]: refs.append("LG-CONTRACT-ALLOWED")
        if ctype == "removed" and field in ruleset.RULES["required_fields"]: refs.append(ruleset.RULES["required_fields"][field])
        srcs = sorted({s for c in grp for s in c["sources"]})
        old_v, new_v = main["old"], main["new"]
        if ctype == "moved": verb = f"moved ({main.get('detail', '')})"
        elif ctype == "removed": verb = "is missing on the revised label"
        elif ctype == "added": verb = "was added on the revised label"
        else: verb = f"changed from '{_fmt(old_v)}' to '{_fmt(new_v)}'"
        expl = f"{label} {verb}. {why}"
        if field == "udi":
            bc = [c for c in grp if "barcode" in c["sources"]]
            if bc: expl += f" Barcode payload: {_fmt(bc[0]['old'])} → {_fmt(bc[0]['new'])}."
        findings.append({"field": field, "field_label": label, "classification": cls, "severity": sev, "change_type": ctype,
                         "title": f"{label}: {ctype}", "old_value": old_v, "new_value": new_v, "contract_statement": why,
                         "sources": srcs, "evidence": [_evidence(c) for c in grp], "explanation": expl,
                         "recommended_action": ACTIONS[cls], "rule_refs": refs, "status": "OPEN"})
    # requested change not found
    for a in contract["allowed_changes"]:
        if a["field"] not in changed_fields:
            findings.append({"field": a["field"], "field_label": ruleset.label(a["field"]), "classification": "UNEXPECTED", "severity": "major",
                "change_type": "missing_requested_change", "title": f"{ruleset.label(a['field'])}: requested change not found",
                "old_value": None, "new_value": None, "contract_statement": "Requested change is absent from the revised label.", "sources": ["contract"],
                "evidence": [], "explanation": f"The change request expects {ruleset.label(a['field'])} to change, but no difference was detected.",
                "recommended_action": "Confirm the revised artwork includes the requested modification.", "rule_refs": ["LG-CONTRACT-ALLOWED"], "status": "OPEN"})
        else:
            f = next((x for x in findings if x["field"] == a["field"]), None)
            checks.append({"id": "LG-CHK-EXP", "name": f"Requested change applied: {ruleset.label(a['field'])}", "passed": bool(f and f["classification"] == "EXPECTED"), "detail": f"{_fmt(f['old_value'])} → {_fmt(f['new_value'])}" if f else ""})
    # visual regions -> attribute to findings or flag
    pad = ruleset.RULES["tolerances"]["visual_pad_pts"]
    def hit(r, bb): return bb and not (bb[2] + pad < r[0] or bb[0] - pad > r[2] or bb[3] + pad < r[1] or bb[1] - pad > r[3])
    for page, r in visual_regions:
        owner = next((f for f in findings for e in f["evidence"] if e["page"] == page and (hit(r, e["bbox_old"]) or hit(r, e["bbox_new"]))), None)
        if owner:
            if "visual" not in owner["sources"]: owner["sources"].append("visual")
            owner["evidence"].append({"source": "visual", "page": page, "bbox_old": r, "bbox_new": r, "old": None, "new": None})
        else:
            findings.append({"field": "visual_region", "field_label": ruleset.label("visual_region"), "classification": "REQUIRES_REVIEW", "severity": "minor",
                "change_type": "visual_difference", "title": "Unattributed visual difference", "old_value": None, "new_value": None,
                "contract_statement": "A pixel-level difference was found that does not map to any extracted element.", "sources": ["visual"],
                "evidence": [{"source": "visual", "page": page, "bbox_old": r, "bbox_new": r, "old": None, "new": None}],
                "explanation": "A visual difference exists in this region that text, symbol and barcode extraction could not attribute.",
                "recommended_action": ACTIONS["REQUIRES_REVIEW"], "rule_refs": [], "status": "OPEN"})
    # checks: protected unchanged, required present, UDI
    for pf in contract["protected_fields"]:
        bad = next((f for f in findings if f["field"] == pf), None)
        checks.append({"id": "LG-CHK-PROT", "name": f"Protected field unchanged: {ruleset.label(pf)}", "passed": bad is None, "detail": "No difference detected" if bad is None else bad["explanation"]})
    present = {e["field"] for pg in new_pages for e in pg["elements"]}
    for field, rid in ruleset.RULES["required_fields"].items():
        checks.append({"id": rid, "name": f"Required element present: {ruleset.label(field)}", "passed": field in present, "detail": "" if field in present else "Not found on revised label"})
    checks += barcode_validator.udi_checks(old_pages, "approved") + barcode_validator.udi_checks(new_pages, "revised")
    findings.sort(key=lambda f: (CLS_ORDER[f["classification"]], SEV_ORDER[f["severity"]]))
    for i, f in enumerate(findings, 1): f["id"] = f"LG-{i:03d}"
    # attach failed checks to findings
    for f in findings:
        for c in checks:
            if not c["passed"] and c["id"].startswith("LG-REQ") and ruleset.RULES["required_fields"].get(f["field"]) == c["id"] and c["id"] not in f["rule_refs"]: f["rule_refs"].append(c["id"])
    summary = {"passed_checks": sum(c["passed"] for c in checks), "failed_checks": sum(not c["passed"] for c in checks),
               "critical_flags": sum(f["severity"] == "critical" and f["classification"] != "EXPECTED" for f in findings),
               "review_flags": sum(f["classification"] == "REQUIRES_REVIEW" for f in findings),
               "unexpected": sum(f["classification"] == "UNEXPECTED" for f in findings),
               "expected": sum(f["classification"] == "EXPECTED" for f in findings), "total_findings": len(findings)}
    return findings, checks, summary
