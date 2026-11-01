import json, os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from fastapi.testclient import TestClient
os.environ["LG_STORAGE"] = tempfile.mkdtemp()
from app.main import app
S = os.path.join(os.path.dirname(__file__), "..", "sample_data")

def test_end_to_end_demo():
    c = TestClient(app); req = json.load(open(f"{S}/change_request.json"))
    j = c.post("/api/validation-jobs", data=req, files={"old_pdf": open(f"{S}/old_label.pdf", "rb"), "new_pdf": open(f"{S}/revised_label.pdf", "rb")}).json()
    i = j["id"]
    assert c.post(f"/api/validation-jobs/{i}/run").status_code == 409          # contract gate
    k = c.post(f"/api/validation-jobs/{i}/contract").json()
    assert set(k["protected_fields"]) >= {"udi", "safety_warnings", "manufacturer_details", "product_id"}
    c.post(f"/api/validation-jobs/{i}/contract/confirm"); c.post(f"/api/validation-jobs/{i}/run")
    assert c.get(f"/api/validation-jobs/{i}/status").json()["status"] == "REVIEW_REQUIRED"
    F = {f["field"]: f for f in c.get(f"/api/validation-jobs/{i}/findings").json()["findings"]}
    assert F["sterilization_symbol"]["classification"] == "EXPECTED" and F["sterilization_statement"]["classification"] == "EXPECTED"
    assert F["udi"]["classification"] == "UNEXPECTED" and F["udi"]["severity"] == "critical" and "barcode" in F["udi"]["sources"]
    assert F["safety_warnings"]["classification"] == "UNEXPECTED" and F["safety_warnings"]["change_type"] == "removed"
    assert F["logo"]["classification"] == "REQUIRES_REVIEW"
    assert "manufacturer_details" not in F and "product_id" not in F          # protected & unchanged => no finding
    assert c.post(f"/api/validation-jobs/{i}/approvals", json={"reviewer": "qa1", "decision": "APPROVE"}).status_code == 422
    assert c.post(f"/api/validation-jobs/{i}/approvals", json={"reviewer": "qa1", "decision": "REJECT", "comment": "UDI and warning wrong"}).status_code == 200
    assert c.get(f"/api/validation-jobs/{i}/report.pdf").headers["content-type"] == "application/pdf"
    assert len(c.get(f"/api/validation-jobs/{i}/audit").json()) >= 6

def test_identical_labels_no_findings():
    from app.services import pipeline
    d = tempfile.mkdtemp(); contract = {"change_id": "X", "allowed_changes": [], "protected_fields": ["udi"], "requires_human_review": True}
    r = pipeline.run(d, f"{S}/old_label.pdf", f"{S}/old_label.pdf", contract, explain=False)
    assert r["summary"]["total_findings"] == 0 and r["summary"]["failed_checks"] == 0
