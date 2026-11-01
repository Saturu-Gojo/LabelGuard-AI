# ---- build the React frontend
FROM node:20-slim AS fe
WORKDIR /fe
COPY frontend/package.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- API + static frontend in one image
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend backend
COPY sample_data/symbols sample_data/symbols
COPY --from=fe /fe/dist frontend/dist
ENV LG_STORAGE=/data PORT=7860 PYTHONUNBUFFERED=1
RUN mkdir -p /data && chmod 777 /data && useradd -m -u 1000 app && chown -R app /app
USER app
WORKDIR /app/backend
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
