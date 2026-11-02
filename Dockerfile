FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

# Install git and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api/ /app/api/
COPY ingest/ /app/ingest/
COPY index/ /app/index/
COPY retrieve/ /app/retrieve/
COPY generate/ /app/generate/
COPY samples/ /app/samples/
COPY build_index.py /app/
COPY run_ingest.py /app/

# Create data directory for cache and persistent storage
RUN mkdir -p /app/data/embed_cache /app/data/repos /app/data/qdrant_local

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

