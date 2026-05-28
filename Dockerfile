# ── Base image ────────────────────────────────────
# Python 3.11 slim = smaller image, same Python we use locally
FROM python:3.11-slim

# ── Working directory inside the container ────────
WORKDIR /app

# ── Install dependencies first (layer caching) ────
# Copying requirements before source code means Docker
# only re-installs packages when requirements.txt changes,
# not on every code change. This saves minutes per build.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Copy source code ──────────────────────────────
COPY . .

# ── Expose the port FastAPI runs on ───────────────
EXPOSE 8000

# ── Start the app ─────────────────────────────────
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]