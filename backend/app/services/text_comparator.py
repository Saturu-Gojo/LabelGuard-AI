"""Text + symbol comparison engine: field-level diff of old vs new structured elements."""
from difflib import SequenceMatcher
from rapidfuzz import fuzz
from . import ruleset

def _group(pages, types):
    g = {}
    for pg in pages:
        for e in pg["elements"]:
            if e["type"] in types and e["field"] != "ignored":
                g.setdefault(e["field"], []).append({**e, "page": pg["page"]})
    return g

def _union(els):
    return [min(e["bbox"][0] for e in els), min(e["bbox"][1] for e in els), max(e["bbox"][2] for e in els), max(e["bbox"][3] for e in els)]

def word_diff(old, new):
    a, b = old.split(), new.split(); ops = []
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, a, b).get_opcodes():
        if tag != "equal": ops.append({"op": tag, "old": " ".join(a[i1:i2]), "new": " ".join(b[j1:j2])})
    return ops

def compare(old_pages, new_pages):
    changes = []; tol = ruleset.RULES["tolerances"]
    o, n = _group(old_pages, {"text"}), _group(new_pages, {"text"})
    for field in sorted(set(o) | set(n)):
        oe, ne = o.get(field), n.get(field)
        if field == "other_text":
            changes += _compare_other(oe or [], ne or []); continue
        if oe and not ne:
            changes.append(_chg(field, "removed", " ".join(e["value"] for e in oe), None, oe[0]["page"], None, _union(oe), "text"))
        elif ne and not oe:
            changes.append(_chg(field, "added", None, " ".join(e["value"] for e in ne), ne[0]["page"], _union(ne), None, "text"))
        else:
            ov, nv = " ".join(e["value"] for e in oe), " ".join(e["value"] for e in ne)
            if ov != nv:
                c = _chg(field, "modified", ov, nv, ne[0]["page"], _union(ne), _union(oe), "text"); c["diff"] = word_diff(ov, nv); changes.append(c)
    # symbols (identity + position)
    os_, ns = _group(old_pages, {"symbol"}), _group(new_pages, {"symbol"})
    for field in sorted(set(os_) | set(ns)):
        oe, ne = os_.get(field), ns.get(field)
        if oe and not ne: changes.append(_chg(field, "removed", oe[0]["value"], None, oe[0]["page"], None, oe[0]["bbox"], "symbol"))
        elif ne and not oe: changes.append(_chg(field, "added", None, ne[0]["value"], ne[0]["page"], ne[0]["bbox"], None, "symbol"))
        else:
            a, b = oe[0], ne[0]
            if a["value"] != b["value"]:
                changes.append(_chg(field, "modified", a["value"], b["value"], b["page"], b["bbox"], a["bbox"], "symbol"))
            elif max(abs(x - y) for x, y in zip(a["bbox"], b["bbox"])) > tol["position_pts"]:
                dx, dy = round(b["bbox"][0] - a["bbox"][0], 1), round(b["bbox"][1] - a["bbox"][1], 1)
                c = _chg(field, "moved", f"x={a['bbox'][0]}, y={a['bbox'][1]}", f"x={b['bbox'][0]}, y={b['bbox'][1]}", b["page"], b["bbox"], a["bbox"], "symbol")
                c["detail"] = f"Shifted by ({dx}, {dy}) pt"; changes.append(c)
        if ne and ne[0]["value"] == "unknown_symbol":
            changes.append(_chg(field, "unrecognised", None, "unknown_symbol", ne[0]["page"], ne[0]["bbox"], None, "symbol"))
    return changes

def _compare_other(oe, ne):
    out, used = [], set()
    for a in oe:
        best, bs = None, 0
        for j, b in enumerate(ne):
            s = fuzz.ratio(a["value"], b["value"])
            if j not in used and s > bs: best, bs = j, s
        if best is not None and bs >= ruleset.RULES["tolerances"]["text_fuzzy_pair"]:
            used.add(best); b = ne[best]
            if a["value"] != b["value"]:
                c = _chg("other_text", "modified", a["value"], b["value"], b["page"], b["bbox"], a["bbox"], "text"); c["diff"] = word_diff(a["value"], b["value"]); out.append(c)
        else:
            out.append(_chg("other_text", "removed", a["value"], None, a["page"], None, a["bbox"], "text"))
    for j, b in enumerate(ne):
        if j not in used: out.append(_chg("other_text", "added", None, b["value"], b["page"], b["bbox"], None, "text"))
    return out

def _chg(field, ctype, old, new, page, bbox_new, bbox_old, source):
    return {"field": field, "change_type": ctype, "old": old, "new": new, "page": page, "bbox_new": bbox_new, "bbox_old": bbox_old, "sources": [source]}
