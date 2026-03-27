FROM python:3.12-slim
WORKDIR /app

# System deps + Node.js (needed for MCP servers via npx)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl wget nodejs npm && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[all]"

RUN mkdir -p /app/data

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
