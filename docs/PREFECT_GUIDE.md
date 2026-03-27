# QYNE v1 — Prefect Workers Guide

## How Prefect Works in QYNE

Prefect is the orchestration layer for all deterministic background tasks (no AI, no tokens).
It runs Python scripts on a schedule or on-demand, with retries, logging, and a dashboard.

### Architecture

```
Prefect Server (qyne-prefect:4200)     ← Stores state, schedules, logs
    │
    ▼
Prefect Worker (qyne-prefect-worker)   ← Polls for work, executes flows
    │
    ├── flow: scraper_latam            ← Crawl4AI → Directus
    ├── flow: etl_documents            ← Docling → Directus + LanceDB
    └── flow: (your custom flows)      ← Any Python → Directus
```

### What Prefect OSS CAN do
- Run flows on cron schedules
- Retry failed tasks automatically
- Dashboard with logs, timeline, state tracking
- Durable execution (resume from failure)
- API to trigger flows: `POST /api/deployments/{id}/create_flow_run`
- Concurrent task execution
- Artifacts (save results, charts, tables)

### What Prefect OSS CANNOT do (Cloud only)
- Webhooks (receive external HTTP triggers)
- Automations (event-driven triggers)
- SLAs and alerts
- RBAC and SSO

### Workaround for webhooks
Use n8n as the webhook receiver. n8n calls Prefect API to trigger flows:
```
External service → webhook → n8n → HTTP POST → Prefect API → flow runs
```

## Writing Flows — Best Practices

### Pattern 1: Simple ETL (most common)

```python
from prefect import flow, task
from prefect.logging import get_run_logger
import httpx

DIRECTUS_URL = "http://directus:8055"
DIRECTUS_TOKEN = os.getenv("DIRECTUS_TOKEN", "")

@task(retries=3, retry_delay_seconds=30)
def extract(url: str) -> str:
    """Fetch data from external source."""
    return httpx.get(url, timeout=30).text

@task
def transform(raw: str) -> list[dict]:
    """Parse and clean data. Deterministic, no AI."""
    # Your parsing logic here
    return [{"title": "...", "content": "..."}]

@task(retries=2, retry_delay_seconds=10)
def load(items: list[dict], collection: str = "scraped_data"):
    """Save to Directus via REST API."""
    logger = get_run_logger()
    headers = {"Authorization": f"Bearer {DIRECTUS_TOKEN}", "Content-Type": "application/json"}
    for item in items:
        r = httpx.post(f"{DIRECTUS_URL}/items/{collection}", json=item, headers=headers, timeout=10)
        if r.is_success:
            logger.info(f"Saved: {item.get('title', 'unknown')}")

@flow(name="My ETL Flow", log_prints=True)
def my_etl(urls: list[str] | None = None):
    for url in (urls or []):
        raw = extract(url)
        items = transform(raw)
        load(items)
```

### Pattern 2: Document Processing (Docling)

```python
@task(retries=2)
def parse_document(file_path: str) -> dict:
    from docling.document_converter import DocumentConverter
    converter = DocumentConverter()
    result = converter.convert(file_path)
    return {"title": Path(file_path).stem, "content": result.document.export_to_markdown()}

@task
def index_in_knowledge(doc: dict):
    """Write embeddings to LanceDB (shared volume with Agno)."""
    from agno.knowledge.knowledge import Knowledge
    from agno.vectordb.lancedb import LanceDb, SearchType
    from agno.knowledge.embedder.voyageai import VoyageAIEmbedder

    kb = Knowledge(vector_db=LanceDb(
        table_name="knowledge",
        uri="/app/data/lancedb",
        search_type=SearchType.hybrid,
        embedder=VoyageAIEmbedder(id="voyage-3-lite", dimensions=512),
    ))
    kb.insert(content=doc["content"], metadata={"title": doc["title"]})

@flow(name="Document ETL")
def etl_documents(file_paths: list[str]):
    for path in file_paths:
        doc = parse_document(path)
        load([doc], collection="documents")  # Save text to Directus
        index_in_knowledge(doc)               # Save embeddings to LanceDB
```

### Pattern 3: Scheduled Backup

```python
import subprocess

@task
def backup_postgres():
    """Dump Directus database to file."""
    subprocess.run([
        "pg_dump", "-h", "postgres", "-U", "directus_user", "-d", "directus_db",
        "-f", "/tmp/directus_backup.sql"
    ], check=True)
    return "/tmp/directus_backup.sql"

@task
def upload_to_rustfs(file_path: str):
    """Upload backup to RustFS (S3)."""
    # Use boto3 or httpx to upload to http://rustfs:9000
    pass

@flow(name="Database Backup")
def backup_flow():
    path = backup_postgres()
    upload_to_rustfs(path)
```

## Deploying Flows

### Method 1: serve() — Simple, recommended for QYNE

```python
# At the bottom of your flow file:
if __name__ == "__main__":
    my_etl.serve(
        name="my-etl-deployment",
        cron="0 */6 * * *",  # Every 6 hours
        parameters={"urls": ["https://example.com/data"]},
    )
```

### Method 2: deploy() — For work pool based execution

```python
if __name__ == "__main__":
    my_etl.deploy(
        name="my-etl-deployment",
        work_pool_name="default-pool",
        cron="0 */6 * * *",
    )
```

### Method 3: Via API (triggered by n8n or Agno)

```bash
# Create deployment first, then trigger via API:
curl -X POST http://prefect:4200/api/deployments/{deployment_id}/create_flow_run \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"urls": ["https://example.com"]}}'
```

## Rules for QYNE Flows

1. **All business data goes to Directus** via REST API. Never write to PostgreSQL directly.
2. **Knowledge embeddings go to LanceDB** via shared volume (`/app/data/lancedb`).
3. **No AI in flows.** Flows are deterministic. If you need AI, use Agno agents.
4. **Use `@task` for each step.** This gives you retries, logging, and visibility per step.
5. **Use `retries=` on tasks that call external services.** Network calls fail.
6. **Log with `get_run_logger()`**, not `print()`. Logs appear in Prefect dashboard.
7. **Keep flows small.** One flow = one pipeline. Don't combine scraping + ETL + backup.

## Triggering Flows from Other Services

### From n8n (webhook → Prefect)
```
n8n HTTP Request node → POST http://prefect:4200/api/deployments/{id}/create_flow_run
```

### From Agno (agent decides to trigger)
```python
# In Agno tool:
httpx.post("http://prefect:4200/api/deployments/{id}/create_flow_run", json={"parameters": {...}})
```

### From Directus (via n8n bridge)
```
Directus trigger → n8n workflow → HTTP POST → Prefect API
```
