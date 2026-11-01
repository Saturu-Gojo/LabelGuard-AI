import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
NAVY = colors.HexColor("#0B2545"); CY = colors.HexColor("#13A8C9")
CLS = {"UNEXPECTED": colors.HexColor("#C62828"), "REQUIRES_REVIEW": colors.HexColor("#E08A00"), "EXPECTED": colors.HexColor("#2E7D32")}

def build(path, job, result, approvals=()):
    ss = getSampleStyleSheet(); sm = ParagraphStyle("sm", parent=ss["Normal"], fontSize=8, leading=10)
    h = ParagraphStyle("h", parent=ss["Heading2"], textColor=NAVY); doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=14*mm, bottomMargin=14*mm)
    s = result["summary"]; st = []
    st += [Paragraph("LabelGuard AI — Label Inspection Report", ParagraphStyle("t", parent=ss["Title"], textColor=NAVY)),
           Paragraph(f"{job['product_id']} · {job['product_name']} · {job['old_version']} → {job['new_version']} · {job['market']} · {job['language']}", ss["Normal"]),
           Paragraph(f"Change request {result['contract']['change_id']}: {job.get('change_reason','')}  |  Ruleset {result['ruleset_version']}", sm),
           Paragraph(f"Approved label SHA-256: {result['documents']['old_sha256'][:24]}…  Revised label SHA-256: {result['documents']['new_sha256'][:24]}…", sm), Spacer(1, 6)]
    t = Table([["Passed checks", "Failed checks", "Critical flags", "Unexpected", "Review flags", "Expected"],
               [s["passed_checks"], s["failed_checks"], s["critical_flags"], s["unexpected"], s["review_flags"], s["expected"]]], colWidths=[30*mm]*6)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                           ("FONTSIZE", (0, 1), (-1, 1), 16), ("GRID", (0, 0), (-1, -1), .5, colors.lightgrey), ("FONTSIZE", (0, 0), (-1, 0), 8)]))
    verdict = "REVIEW REQUIRED — do not release" if s["unexpected"] or s["review_flags"] else "No discrepancies detected"
    st += [t, Spacer(1, 6), Paragraph(f"<b>Outcome:</b> {verdict}", ss["Normal"]), Paragraph("Findings", h)]
    for f in result["findings"]:
        col = CLS[f["classification"]]
        rows = [[Paragraph(f"<b>{f['id']} — {f['title']}</b>", sm), Paragraph(f"<font color='{col.hexval()}'><b>{f['classification']}</b></font> · {f['severity']}", sm)],
                [Paragraph(f"<b>Previous:</b> {f['old_value'] or '—'}<br/><b>New:</b> {f['new_value'] or '—'}<br/><b>Contract:</b> {f['contract_statement']}<br/><b>Detected by:</b> {', '.join(f['sources'])}<br/>"
                           f"<b>Evidence:</b> " + "; ".join(f"p{e['page']} {e['source']} {e['bbox_new'] or e['bbox_old']}" for e in f['evidence']) +
                           f"<br/><b>Explanation:</b> {f.get('explanation_ai') or f['explanation']}<br/><b>Action:</b> {f['recommended_action']}<br/><b>Rules:</b> {', '.join(f['rule_refs']) or '—'}", sm), ""]]
        tb = Table(rows, colWidths=[125*mm, 55*mm]); tb.setStyle(TableStyle([("SPAN", (0, 1), (1, 1)), ("BOX", (0, 0), (-1, -1), .8, col), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F6FA")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        st += [KeepTogether([tb, Spacer(1, 5)])]
    st += [PageBreak(), Paragraph("Visual comparison (approved → revised)", h)]
    adir = os.path.join(os.path.dirname(path), "artifacts")
    for pg, o in result["overlays"].items():
        st.append(Table([[Image(os.path.join(adir, o["old"]), 85*mm, 120*mm, kind="proportional"), Image(os.path.join(adir, o["new"]), 85*mm, 120*mm, kind="proportional")]]))
    st += [Paragraph("Validation checks", h)]
    ct = Table([["Check", "Result", "Detail"]] + [[Paragraph(c["name"], sm), "PASS" if c["passed"] else "FAIL", Paragraph(str(c["detail"])[:90], sm)] for c in result["checks"]], colWidths=[85*mm, 18*mm, 77*mm])
    ct.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), .3, colors.lightgrey), ("FONTSIZE", (0, 0), (-1, -1), 8)] +
                           [("TEXTCOLOR", (1, i), (1, i), colors.HexColor("#2E7D32") if c["passed"] else colors.HexColor("#C62828")) for i, c in enumerate(result["checks"], 1)]))
    st += [ct, Paragraph("Review & approval history", h)]
    if approvals:
        for a in approvals: st.append(Paragraph(f"{a['timestamp']} — <b>{a['decision']}</b> by {a['reviewer']}: {a.get('comment','')}", sm))
    else: st.append(Paragraph("No reviewer decision recorded yet.", sm))
    st += [Spacer(1, 10), Paragraph(result["disclaimer"] + " The prototype validates against the supplied change contract and configured reference rules; it does not establish regulatory compliance. Approval must follow the organisation's controlled quality process.", sm)]
    doc.build(st); return path
