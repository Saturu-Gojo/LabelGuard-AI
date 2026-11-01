import base64, hmac, json, os, shutil, time, uuid
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .services import contract_generator, pipeline, report_generator

ROOT = os.environ.get("LG_STORAGE", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage"))
os.makedirs(ROOT, exist_ok=True)
app = FastAPI(title="LabelGuard AI")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
MAX_UPLOAD = int(os.environ.get("LG_MAX_UPLOAD_MB", "15")) * 1024 * 1024

@app.middleware("http")
async def basic_auth(request, call_next):
    """Optional shared-password gate for public demos: set LG_BASIC_PASS (and optionally LG_BASIC_USER)."""
    pw = os.environ.get("LG_BASIC_PASS")
    if pw and request.url.path != "/api/health":
        user = os.environ.get("LG_BASIC_USER", "labelguard"); ok = False
        h = request.headers.get("authorization", "")
        if h.startswith("Basic "):
            try:
                u, _, p = base64.b64decode(h[6:]).decode().partition(":")
                ok = hmac.compare_digest(u, user) and hmac.compare_digest(p, pw)
            except Exception: pass
        if not ok: return Response("Authentication required", 401, headers={"WWW-Authenticate": 'Basic realm="LabelGuard AI"'})
    return await call_next(request)

def jd(i): 
    d = os.path.join(ROOT, i)
    if not os.path.isdir(d): raise HTTPException(404, "Job not found")
    return d
def load(i): return json.load(open(os.path.join(jd(i), "job.json")))
def save(i, job): json.dump(job, open(os.path.join(jd(i), "job.json"), "w"), indent=2)
def audit(i, actor, action, detail=""):
    with open(os.path.join(jd(i), "audit.jsonl"), "a") as f: f.write(json.dumps({"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "actor": actor, "action": action, "detail": detail}) + "\n")

@app.get("/api/health")
def health(): return {"ok": True}

@app.post("/api/validation-jobs")
async def create_job(product_id: str = Form(...), product_name: str = Form(""), market: str = Form("EU"), language: str = Form("English"),
                     old_version: str = Form("V1"), new_version: str = Form("V2"), change_reason: str = Form(""), change_request: str = Form(...),
                     user: str = Form("demo.user"), old_pdf: UploadFile = File(...), new_pdf: UploadFile = File(...)):
    for up in (old_pdf, new_pdf):
        head = up.file.read(5); up.file.seek(0, 2); size = up.file.tell(); up.file.seek(0)
        if head != b"%PDF-": raise HTTPException(400, f"{up.filename} is not a PDF file")
        if size > MAX_UPLOAD: raise HTTPException(413, f"{up.filename} exceeds the {MAX_UPLOAD // 1048576} MB upload limit")
    i = uuid.uuid4().hex[:10]; os.makedirs(os.path.join(ROOT, i))
    for name, up in (("old.pdf", old_pdf), ("new.pdf", new_pdf)):
        with open(os.path.join(ROOT, i, name), "wb") as f: shutil.copyfileobj(up.file, f)
    job = dict(id=i, product_id=product_id, product_name=product_name, market=market, language=language, old_version=old_version, new_version=new_version,
               change_reason=change_reason, change_request=change_request, status="UPLOADED", created_by=user, created_at=time.strftime("%Y-%m-%dT%H:%M:%S"), contract=None, approvals=[])
    save(i, job); audit(i, user, "JOB_CREATED", f"{product_id} {old_version}->{new_version}"); return job

@app.post("/api/validation-jobs/{i}/contract")
def gen_contract(i: str):
    job = load(i); job["contract"] = contract_generator.generate(job["change_request"], f"CHG-{i[:4].upper()}", job["change_reason"])
    job["status"] = "CONTRACT_PENDING"; save(i, job); audit(i, "system", "CONTRACT_GENERATED", job["contract"]["generated_by"]); return job["contract"]

class Contract(BaseModel):
    change_id: str; reason: str = ""; allowed_changes: list; protected_fields: list; requires_human_review: bool = True
@app.post("/api/validation-jobs/{i}/contract/confirm")
def confirm(i: str, body: Contract | None = None, user: str = "demo.user"):
    job = load(i)
    if body: job["contract"] = {**body.model_dump(), "generated_by": (job["contract"] or {}).get("generated_by", "manual") + "+edited"}
    if not job["contract"]: raise HTTPException(400, "Generate a contract first")
    job["contract"]["status"] = "CONFIRMED"; job["contract"]["confirmed_by"] = user; job["status"] = "QUEUED"; save(i, job)
    audit(i, user, "CONTRACT_CONFIRMED", json.dumps({k: job["contract"][k] for k in ("allowed_changes", "protected_fields")})); return job["contract"]

def _work(i):
    job = load(i); job["status"] = "PROCESSING"; save(i, job)
    try:
        res = pipeline.run(jd(i), os.path.join(jd(i), "old.pdf"), os.path.join(jd(i), "new.pdf"), job["contract"])
        job = load(i); job["status"] = "REVIEW_REQUIRED"; job["summary"] = res["summary"]; save(i, job)
        report_generator.build(os.path.join(jd(i), "report.pdf"), job, res); audit(i, "system", "INSPECTION_COMPLETE", json.dumps(res["summary"]))
    except Exception as e:
        job = load(i); job["status"] = "FAILED"; job["error"] = str(e); save(i, job); audit(i, "system", "INSPECTION_FAILED", str(e))

@app.post("/api/validation-jobs/{i}/run")
def run(i: str, bg: BackgroundTasks):
    job = load(i)
    if not job["contract"] or job["contract"].get("status") != "CONFIRMED": raise HTTPException(409, "Contract must be confirmed before inspection")
    job["status"] = "QUEUED"; save(i, job); bg.add_task(_work, i); audit(i, "system", "INSPECTION_STARTED"); return {"id": i, "status": "QUEUED"}

@app.get("/api/validation-jobs")
def list_jobs(): return sorted([json.load(open(os.path.join(ROOT, d, "job.json"))) for d in os.listdir(ROOT) if os.path.exists(os.path.join(ROOT, d, "job.json"))], key=lambda j: j["created_at"], reverse=True)
@app.get("/api/validation-jobs/{i}")
def get_job(i: str): return load(i)
@app.get("/api/validation-jobs/{i}/status")
def status(i: str): j = load(i); return {"id": i, "status": j["status"], "error": j.get("error")}
def _res(i):
    p = os.path.join(jd(i), "result.json")
    if not os.path.exists(p): raise HTTPException(409, "Inspection not complete")
    return json.load(open(p))
@app.get("/api/validation-jobs/{i}/findings")
def findings(i: str): r = _res(i); return {"summary": r["summary"], "findings": r["findings"], "checks": r["checks"]}
@app.get("/api/validation-jobs/{i}/report")
def report(i: str): r = _res(i); r.pop("elements", None); return {**r, "job": load(i), "audit": audit_log(i)}
@app.get("/api/validation-jobs/{i}/report.pdf")
def report_pdf(i: str):
    job = load(i); res = _res(i); p = os.path.join(jd(i), "report.pdf"); report_generator.build(p, job, res, job["approvals"]); return FileResponse(p, media_type="application/pdf", filename=f"LabelGuard_{job['product_id']}_{i}.pdf")
@app.get("/api/validation-jobs/{i}/files/{name}")
def files(i: str, name: str):
    p = os.path.join(jd(i), "artifacts", os.path.basename(name))
    if not os.path.exists(p): raise HTTPException(404)
    return FileResponse(p)
@app.get("/api/validation-jobs/{i}/pdf/{which}")
def pdf(i: str, which: str):
    if which not in ("old", "new"): raise HTTPException(404)
    return FileResponse(os.path.join(jd(i), f"{which}.pdf"), media_type="application/pdf")

class Approval(BaseModel):
    reviewer: str; role: str = "QA"; decision: str; comment: str = ""
@app.post("/api/validation-jobs/{i}/approvals")
def approve(i: str, a: Approval):
    job = load(i); res = _res(i)
    if a.decision not in ("APPROVE", "REJECT", "REQUEST_CORRECTION"): raise HTTPException(400, "Invalid decision")
    open_flags = res["summary"]["critical_flags"] + res["summary"]["unexpected"]
    if a.decision == "APPROVE" and open_flags and len(a.comment.strip()) < 10:
        raise HTTPException(422, "Approving with unresolved unexpected/critical findings requires a documented justification (min 10 chars)")
    rec = {**a.model_dump(), "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "open_flags_at_decision": open_flags}
    job["approvals"].append(rec); job["status"] = {"APPROVE": "APPROVED", "REJECT": "REJECTED", "REQUEST_CORRECTION": "REVIEW_REQUIRED"}[a.decision]; save(i, job)
    audit(i, a.reviewer, f"DECISION_{a.decision}", a.comment); return rec
def audit_log(i):
    p = os.path.join(jd(i), "audit.jsonl"); return [json.loads(l) for l in open(p)] if os.path.exists(p) else []
@app.get("/api/validation-jobs/{i}/audit")
def audit_ep(i: str): return audit_log(i)


# Serve the built React app from the same origin (single-container deploy). Must stay last so /api routes win.
_FE = os.environ.get("LG_FRONTEND", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist"))
if os.path.isdir(_FE): app.mount("/", StaticFiles(directory=_FE, html=True), name="frontend")
