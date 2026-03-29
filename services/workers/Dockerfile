FROM python:3.12-slim

WORKDIR /app

# System deps + Playwright browser dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Install Playwright browsers + system deps for Crawl4AI
RUN playwright install chromium && playwright install-deps chromium

COPY . .

# Ensure flows are importable
ENV PYTHONPATH=/app

CMD ["prefect", "worker", "start", "--pool", "default-pool", "--type", "process"]
