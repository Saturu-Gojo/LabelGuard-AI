# Deploying LabelGuard AI

One Docker image serves the API and the React app on a single port (default 7860).

## Environment variables
| Variable | Purpose |
|---|---|
| PORT | Listen port (platform usually sets it) |
| LG_BASIC_PASS | Turns on a shared-password login (user `labelguard`, or set LG_BASIC_USER). Strongly recommended on any public URL |
| ANTHROPIC_API_KEY | Optional: LLM contract extraction + explanations. Without it the rule-based path is used |
| LG_STORAGE | Where jobs are stored (default /data) |
| LG_MAX_UPLOAD_MB | Per-PDF upload limit (default 15) |

## Local check
    docker compose up --build        # http://localhost:8000

## Option A - Hugging Face Spaces (free, easiest for a demo)
1. New Space -> SDK: Docker.
2. Push this folder to the Space repo. The Space README.md must start with:
   ---
   title: LabelGuard AI
   sdk: docker
   app_port: 7860
   ---
3. Space settings -> Variables and secrets: add LG_BASIC_PASS (and optionally ANTHROPIC_API_KEY as a secret).
   Also set LG_STORAGE=/tmp/lg (the Space disk is only writable under /tmp).

## Option B - Render
Push to GitHub -> New Blueprint (reads render.yaml) -> set LG_BASIC_PASS. Free tier sleeps when idle (first load ~30-60 s)
and its disk is ephemeral, so uploaded jobs disappear on restart. Fine for a demo; use a paid disk for real use.

## Option C - Any VPS
    docker build -t labelguard . && docker run -d -p 80:7860 -v lg-data:/data -e LG_BASIC_PASS=choose-one labelguard
Put it behind HTTPS (Caddy or nginx) before sharing.

## Before you share the URL
- Set LG_BASIC_PASS. There is no per-user login yet, so anyone with the password sees all jobs.
- Only upload fictional or non-confidential labels; storage is not encrypted and nothing is auto-deleted.
- If ANTHROPIC_API_KEY is set, the change-request text and finding summaries (not the PDFs) are sent to the Claude API.
- Demo data and rules are fictional; this is not a validated medical-device quality system.
