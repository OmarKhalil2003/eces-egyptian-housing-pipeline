# ==============================================================================
# ECES Egyptian Housing Market Dataset Pipeline
# Production Dockerfile
# ==============================================================================
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    ALGOLIA_APP_ID=LL8IZ711CS \
    ALGOLIA_SEARCH_API_KEY=07de0a8209b2f3cd921152dfe39310a9 \
    GEMINI_MODEL=gemini-3.1-flash-lite

# Set working directory inside container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications first for Docker layer caching
COPY requirements.txt pyproject.toml ./

# Upgrade pip and install all dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install -e .

# Copy application source code, evaluation suites, cached data, and runners
COPY . .

# Ensure data and evaluation directories exist
RUN mkdir -p /app/data/raw/details /app/data/output /app/evaluation

# Default execution: run the entire pipeline end-to-end (deterministic engine)
CMD ["python", "run.py", "--all"]
