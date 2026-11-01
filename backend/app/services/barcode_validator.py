"""UDI validation engine: decode, parse GS1 AIs, check digits, compare machine-readable vs human-readable."""
import re

def gs1_check_digit_ok(gtin):
    if not re.fullmatch(r"\d{8}|\d{12,14}", gtin or ""): return False
    body, chk = gtin[:-1], int(gtin[-1])
    s = sum(int(c) * (3 if i % 2 == 0 else 1) for i, c in enumerate(reversed(body)))
    return (10 - s % 10) % 10 == chk

def parse_gs1(text):
    """Supports '(01)<gtin>' and raw '01<gtin>' (+ optional AI 17/10/21 fixed forms)."""
    t = (text or "").replace("(", "").replace(")", "").replace(" ", "")
    out = {}
    m = re.match(r"01(\d{14})", t)
    if m:
        out["gtin"] = m.group(1); rest = t[15:]
        m2 = re.match(r"17(\d{6})", rest)
        if m2: out["expiry"] = m2.group(1); rest = rest[8:]
        if rest.startswith("10"): out["lot"] = rest[2:]
    return out

def printed_udi(pages):
    for pg in pages:
        for e in pg["elements"]:
            if e["type"] == "text" and e["field"] == "udi":
                m = re.search(r"\(?01\)?\s*(\d{14})", e["value"])
                if m: return m.group(1), e
    return None, None

def decoded_udi(pages):
    for pg in pages:
        for e in pg["elements"]:
            if e["type"] == "barcode": return parse_gs1(e["value"]), e
    return {}, None

def compare_barcodes(old_pages, new_pages):
    """Detected-change records for the barcode payload."""
    o, oe = decoded_udi(old_pages); n, ne = decoded_udi(new_pages); out = []
    if oe and not ne:
        out.append({"field": "udi", "change_type": "removed", "old": oe["value"], "new": None, "page": 1, "bbox_new": None, "bbox_old": oe["bbox"], "sources": ["barcode"]})
    elif ne and not oe:
        out.append({"field": "udi", "change_type": "added", "old": None, "new": ne["value"], "page": 1, "bbox_new": ne["bbox"], "bbox_old": None, "sources": ["barcode"]})
    elif oe and ne and oe["value"] != ne["value"]:
        out.append({"field": "udi", "change_type": "modified", "old": oe["value"], "new": ne["value"], "page": 1, "bbox_new": ne["bbox"], "bbox_old": oe["bbox"], "sources": ["barcode"]})
    return out

def udi_checks(pages, which):
    """Deterministic checks for one label. Returns list of {id,name,passed,detail}."""
    parsed, be = decoded_udi(pages); printed, te = printed_udi(pages); checks = []
    if be:
        g = parsed.get("gtin")
        checks.append({"id": f"LG-UDI-001:{which}", "name": f"[{which}] Barcode decodes to a GS1 GTIN", "passed": bool(g), "detail": be["value"]})
        if g: checks.append({"id": f"LG-UDI-002:{which}", "name": f"[{which}] GTIN check digit valid", "passed": gs1_check_digit_ok(g), "detail": g})
    else:
        checks.append({"id": f"LG-UDI-001:{which}", "name": f"[{which}] Barcode present and decodable", "passed": False, "detail": "No barcode decoded"})
    if be and printed:
        checks.append({"id": f"LG-UDI-003:{which}", "name": f"[{which}] Barcode matches printed UDI", "passed": parsed.get("gtin") == printed, "detail": f"barcode={parsed.get('gtin')} printed={printed}"})
    return checks
