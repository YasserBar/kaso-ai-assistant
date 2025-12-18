# Backend Dockerfile for FastAPI (uvicorn)
# Uses Python 3.11 slim and installs required system deps for some Python packages

FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logs
# Increase HuggingFace timeouts significantly for slow connections
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_DOWNLOAD_TIMEOUT=300 \
    HF_HUB_ETAG_TIMEOUT=300 \
    TRANSFORMERS_OFFLINE=0 \
    HF_HOME=/app/data/hf_cache

WORKDIR /app

# Install build tools and libraries needed by lxml and other deps
# build-essential covers gcc, make, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY . .

# Ensure data directories exist (for SQLite and ChromaDB persistence)
RUN mkdir -p data/raw data/processed data/chunks data/chroma_db data/hf_cache

# Expose backend port
EXPOSE 8000

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=120s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Start FastAPI via uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]