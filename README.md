# LabelGuard AI — backend + React frontend

## Run
    cd backend && pip install -r requirements.txt
    cd ../sample_data && python generate_samples.py      # regenerates test labels
    cd ../backend && uvicorn app.main:app --reload       # API docs at http://localhost:8000/docs
    cd .. && pytest tests -q

Optional: `export ANTHROPIC_API_KEY=...` enables LLM contract extraction + reviewer-friendly explanations.
Without it, a deterministic heuristic parser is used. Contract is always user-confirmed before inspection.

## Flow (matches the design doc)
POST /api/validation-jobs (multipart) -> POST .../contract -> POST .../contract/confirm -> POST .../run
-> GET .../status -> GET .../findings | .../report | .../report.pdf -> POST .../approvals -> GET .../audit

## Modules (backend/app/services)
pdf_processor (render, text, barcode, symbol matching) · text_comparator · vision_comparator ·
barcode_validator (GS1 parse, check digit, barcode vs printed) · contract_generator · rules_engine (EXPECTED / UNEXPECTED / REQUIRES_REVIEW + severity) ·
agent_coordinator (LLM wording only; never decides) · report_generator · pipeline

## Notes
- Rules in app/rules/ruleset.json are DEMO rules, not regulatory determinations. Test labels are fictional.
- OCR: embedded PDF text first; Tesseract fallback for scanned pages (PaddleOCR is a drop-in upgrade in pdf_processor._ocr_blocks).
- Storage is file-based per job (storage/<id>/) for speed; swap to PostgreSQL/S3 later.

## Frontend (React + Vite, no extra services)
    cd frontend && npm install && npm run dev      # http://localhost:5173 (proxies /api to :8000)
Demo: New validation -> "Load sample stent labels" -> Generate change contract -> Confirm and run -> Comparison workspace.
Screens: Dashboard, New validation, Change contract, Comparison workspace, Findings, Review and audit.
