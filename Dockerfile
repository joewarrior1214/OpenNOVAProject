FROM python:3.12-slim AS base

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy all source
COPY pyproject.toml README.md ./
COPY nova_syntheia/ nova_syntheia/

# Install
RUN pip install --no-cache-dir .

# Default command (overridden per-service in docker-compose)
CMD ["python", "-m", "nova_syntheia"]
