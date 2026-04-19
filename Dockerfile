# ─────────────────────────────────────────────
# VenueIQ — Dockerfile for Google Cloud Run
# ─────────────────────────────────────────────

# Use official slim Python image for minimal size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy and install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Cloud Run injects PORT env var; default to 8080
ENV PORT=8080

# Expose the port
EXPOSE 8080

# Run with Gunicorn: 2 workers — efficient for Cloud Run
CMD ["gunicorn", "app:app", "--workers", "2", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8080"]
