# Backend Dockerfile for FastAPI (uvicorn)
# Uses Python 3.11 slim and installs required system deps for some Python packages

FROM python:3.11-alpine

# Prevent Python from writing .pyc files and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build tools and libraries needed by lxml and other deps on Alpine
RUN apk add --no-cache \
    build-base \
    gcc \
    libxml2-dev \
    libxslt-dev

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY . .

# Ensure data directories exist (for SQLite and ChromaDB persistence)
RUN mkdir -p data/raw data/processed data/chunks data/chroma_db

# Expose backend port
EXPOSE 8000

# Start FastAPI via uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]