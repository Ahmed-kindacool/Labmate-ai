# syntax=docker/dockerfile:1
# One image, one process: FastAPI serves both the API and the built React app,
# so there is no CORS or API-URL setup. Build:  docker build -t labmate .
#                                       Run:    docker run -p 8000:8000 -e AI_API_KEY=... labmate

# ---- 1. build the frontend --------------------------------------------------
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- 2. runtime -------------------------------------------------------------
FROM python:3.12-slim

# gcc/g++   -> real execution of C / C++ tasks
# antiword  -> legacy .doc uploads
# fonts     -> monospace font for code/output screenshots (Pillow)
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc g++ libc6-dev antiword fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/templates_registry ./templates_registry
COPY --from=frontend /frontend/dist ./frontend_dist

# This container IS the sandbox: student code runs as a locked-down child
# process (rlimits, empty env, dropped to uid 65534 'nobody'). That drop only
# happens when the server runs as root, so do NOT add a USER line here.
# Never bake secrets into the image -- pass AI_API_KEY at runtime.
ENV CODE_EXECUTION_ENABLED=true \
    CODE_EXECUTION_MODE=local \
    CODE_EXECUTION_TIMEOUT_SECONDS=10 \
    FRONTEND_DIST_DIR=/app/frontend_dist \
    ENVIRONMENT=production \
    PYTHONUNBUFFERED=1

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
  CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:%s/api/v1/health' % os.environ.get('PORT','8000'))"

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
