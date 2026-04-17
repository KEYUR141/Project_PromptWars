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

# Run with Gunicorn: 2 workers, 4 threads each — efficient for Cloud Run
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
