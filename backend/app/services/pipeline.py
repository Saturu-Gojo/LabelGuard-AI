import json, os, time
from . import pdf_processor, text_comparator, barcode_validator, vision_comparator, rules_engine, ruleset
COL = {"EXPECTED": (80, 160, 0), "UNEXPECTED": (0, 0, 220), "REQUIRES_REVIEW": (0, 160, 255)}

def run(job_dir, old_pdf, new_pdf, contract, explain=True):
    t0 = time.time(); art = os.path.join(job_dir, "artifacts"); os.makedirs(art, exist_ok=True)
    old = pdf_processor.extract(old_pdf, art, "old"); new = pdf_processor.extract(new_pdf, art, "new")
    changes = text_comparator.compare(old["pages"], new["pages"]) + barcode_validator.compare_barcodes(old["pages"], new["pages"])
    regions, notes = [], []
    if len(old["pages"]) != len(new["pages"]): notes.append(f"Page count differs: {len(old['pages'])} vs {len(new['pages'])}")
    for po, pn in zip(old["pages"], new["pages"]):
        ign = [e["bbox"] for e in po["elements"] + pn["elements"] if e["field"] == "ignored"]
        rs, resized = vision_comparator.diff_regions(po["image"], pn["image"], ign)
        if resized: notes.append(f"Page {po['page']} dimensions differ; revised page was resized for comparison")
        regions += [(po["page"], r) for r in rs]
    findings, checks, summary = rules_engine.analyze(changes, contract, old["pages"], new["pages"], regions)
    if notes:
        for n in notes: findings.append({"id": f"LG-{len(findings)+1:03d}", "field": "document", "field_label": "Document", "classification": "REQUIRES_REVIEW", "severity": "major",
            "change_type": "structure", "title": n, "old_value": None, "new_value": None, "contract_statement": n, "sources": ["pdf"], "evidence": [], "explanation": n,
            "recommended_action": "Confirm page structure matches the approved label.", "rule_refs": [], "status": "OPEN"})
        summary["review_flags"] += len(notes); summary["total_findings"] = len(findings)
    if explain:
        from . import agent_coordinator; agent_coordinator.enrich(findings, contract)
    # overlays
    overlays = {}
    for po, pn in zip(old["pages"], new["pages"]):
        ob, nb = [], []
        for f in findings:
            for e in f["evidence"]:
                if e["page"] != po["page"] or e["source"] == "visual": continue
                if e["bbox_old"]: ob.append((e["bbox_old"], COL[f["classification"]], f["id"]))
                if e["bbox_new"]: nb.append((e["bbox_new"], COL[f["classification"]], f["id"]))
        overlays[po["page"]] = {"old": os.path.basename(vision_comparator.overlay(po["image"], ob, os.path.join(art, f"old_overlay_p{po['page']}.png"))),
                                "new": os.path.basename(vision_comparator.overlay(pn["image"], nb, os.path.join(art, f"new_overlay_p{po['page']}.png")))}
    result = {"ruleset_version": ruleset.RULES["version"], "disclaimer": ruleset.RULES["disclaimer"], "contract": contract,
              "documents": {"old_sha256": old["hash"], "new_sha256": new["hash"]}, "summary": summary, "findings": findings, "checks": checks,
              "overlays": overlays, "pages": {"old": [os.path.basename(p["image"]) for p in old["pages"]], "new": [os.path.basename(p["image"]) for p in new["pages"]]},
              "elements": {"old": [{"page": p["page"], "elements": p["elements"]} for p in old["pages"]], "new": [{"page": p["page"], "elements": p["elements"]} for p in new["pages"]]},
              "processing_seconds": round(time.time() - t0, 2)}
    json.dump(result, open(os.path.join(job_dir, "result.json"), "w"), indent=2, default=str)
    return result
