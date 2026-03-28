# QYNE v1 — Prefect Production Patterns & Flow Reference

## Flow Configuration: Production Defaults

Every production flow should use these settings:

```python
@flow(
    name="Human Readable Name",
    log_prints=True,              # Capture print() in Prefect logs
    retries=1,                    # Flow-level retry on infrastructure failure
    retry_delay_seconds=60,       # Wait before flow retry
    timeout_seconds=3600,         # Kill after 1 hour (adjust per flow)
)
```

Every production task should use these settings:

```python
@task(
    retries=3,                    # Task-level retries
    retry_delay_seconds=[10, 30, 60],  # Exponential backoff
    timeout_seconds=300,          # Kill after 5 minutes
    log_prints=True,
)
```

## Pattern 1: Conditional Retry

Retry only on specific errors (e.g., HTTP 503, rate limits):

```python
from prefect import Task, task
from prefect.client.schemas.objects import TaskRun
from prefect.states import State

def retry_on_rate_limit(task: Task, task_run: TaskRun, state: State) -> bool:
    try:
        state.result()
    except httpx.HTTPStatusError as e:
        return e.response.status_code in (429, 503, 502)
    except (httpx.ConnectTimeout, httpx.ReadTimeout):
        return True
    return False

@task(retries=5, retry_delay_seconds=[5, 15, 30, 60, 120], retry_condition_fn=retry_on_rate_limit)
def fetch_with_backoff(url: str) -> str:
    resp = httpx.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text
```

## Pattern 2: Caching (Skip Expensive Work)

Cache task results to avoid re-running expensive operations:

```python
from prefect import task
from prefect.cache_policies import INPUTS

@task(cache_policy=INPUTS, cache_expiration=timedelta(hours=6))
def expensive_computation(data: str) -> dict:
    # Only runs if inputs changed or cache expired
    return process(data)
```

## Pattern 3: Async Concurrency

Run multiple tasks in parallel using native async:

```python
import asyncio

@task
async def fetch_url(url: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=30)
        return resp.text

@flow
async def parallel_scraper(urls: list[str]) -> list[str]:
    results = await asyncio.gather(*[fetch_url(url) for url in urls])
    return results
```

## Pattern 4: Task Runner Concurrency

Use ThreadPoolTaskRunner for CPU-bound parallel work:

```python
from prefect.task_runners import ThreadPoolTaskRunner

@flow(task_runner=ThreadPoolTaskRunner(max_workers=4))
def parallel_processing(items: list[dict]):
    futures = [process_item.submit(item) for item in items]
    return [f.result() for f in futures]
```

## Pattern 5: State Hooks (Notifications)

Run code when a flow succeeds or fails:

```python
def notify_on_failure(flow, flow_run, state):
    # Send alert to Directus tasks
    httpx.post(f"{DIRECTUS_URL}/items/tasks", json={
        "title": f"FLOW FAILED: {flow.name}",
        "body": f"Run {flow_run.name} failed: {state.message}",
        "status": "todo",
    }, headers=HEADERS)

def log_on_success(flow, flow_run, state):
    httpx.post(f"{DIRECTUS_URL}/items/events", json={
        "type": "flow_success",
        "payload": {"flow": flow.name, "run": flow_run.name},
    }, headers=HEADERS)

@flow(on_failure=[notify_on_failure], on_completion=[log_on_success])
def critical_pipeline():
    ...
```

## Pattern 6: Artifacts (Persist Results)

Save tables, markdown, or links as artifacts visible in the dashboard:

```python
from prefect.artifacts import create_markdown_artifact, create_table_artifact

@flow
def report_flow():
    data = fetch_metrics()

    # Table artifact (visible in Prefect UI)
    create_table_artifact(
        key="weekly-metrics",
        table=[
            {"metric": "contacts", "count": data["contacts"]},
            {"metric": "tickets", "count": data["tickets"]},
        ],
        description="Weekly metrics summary",
    )

    # Markdown artifact
    create_markdown_artifact(
        key="weekly-report",
        markdown=f"# Weekly Report\n\nContacts: {data['contacts']}\nTickets: {data['tickets']}",
    )
```

## Pattern 7: Subflows (Flow Composition)

Call one flow from another:

```python
@flow
def extract():
    return fetch_data()

@flow
def transform(data):
    return clean(data)

@flow
def load(data):
    save_to_directus(data)

@flow
def etl_pipeline():
    data = extract()
    cleaned = transform(data)
    load(cleaned)
```

## Pattern 8: Parameterized Schedules

Different parameters for different schedules:

```python
if __name__ == "__main__":
    # Morning run: full scrape
    property_pipeline.serve(
        name="property-full-scrape",
        cron="0 6 * * *",
        parameters={"sites": ["mercadolibre_ve"], "max_pages": 10, "download_images": True},
    )

    # Evening run: quick check (fewer pages, no images)
    property_pipeline.serve(
        name="property-quick-check",
        cron="0 18 * * *",
        parameters={"sites": ["mercadolibre_ve"], "max_pages": 2, "download_images": False},
    )
```

## Pattern 9: Global Concurrency Limits

Prevent too many flows from running simultaneously:

```python
from prefect import flow
from prefect.concurrency.sync import concurrency

@task
def call_external_api(item):
    with concurrency("external-api", occupy=1):  # Max 1 concurrent call
        return httpx.get(f"https://api.example.com/{item}")

@flow
def rate_limited_flow(items: list[str]):
    for item in items:
        call_external_api(item)
```

## Pattern 10: Transactions (Atomic Operations)

Ensure all-or-nothing execution:

```python
from prefect import task, flow
from prefect.transactions import transaction

@task
def write_to_db(data):
    # If this fails, the transaction rolls back
    httpx.post(f"{DIRECTUS_URL}/items/contacts", json=data, headers=HEADERS)

@task
def send_notification(contact_id):
    httpx.post(f"{DIRECTUS_URL}/items/events", json={
        "type": "contact_created", "payload": {"id": contact_id}
    }, headers=HEADERS)

@flow
def atomic_contact_creation(data: dict):
    with transaction():
        result = write_to_db(data)
        send_notification(result["id"])
        # If notification fails, DB write is rolled back
```

## Pattern 11: Custom Return States

Signal specific outcomes:

```python
from prefect.states import Completed, Failed

@flow
def conditional_flow(data: list):
    if not data:
        return Completed(message="No data to process — skipped")

    try:
        process(data)
        return Completed(message=f"Processed {len(data)} items")
    except Exception as e:
        return Failed(message=f"Processing failed: {e}")
```

## Pattern 12: Runtime Context

Access flow/task metadata during execution:

```python
from prefect.runtime import flow_run, task_run

@task
def context_aware_task():
    logger = get_run_logger()
    logger.info(f"Flow run: {flow_run.name}")
    logger.info(f"Task run: {task_run.name}")
    logger.info(f"Flow parameters: {flow_run.parameters}")
```

## Prefect Integrations (Official Packages)

| Package | Purpose | Install |
|---------|---------|---------|
| prefect-aws | S3, ECS, Lambda, Secrets Manager | `pip install prefect-aws` |
| prefect-gcp | GCS, BigQuery, Cloud Run, Vertex AI | `pip install prefect-gcp` |
| prefect-azure | Blob Storage, ACI, Cosmos DB | `pip install prefect-azure` |
| prefect-docker | Docker containers, images | `pip install prefect-docker` |
| prefect-kubernetes | K8s jobs, pods, deployments | `pip install prefect-kubernetes` |
| prefect-dbt | dbt Core and dbt Cloud | `pip install prefect-dbt` |
| prefect-sqlalchemy | SQL databases (any SQLAlchemy) | `pip install prefect-sqlalchemy` |
| prefect-snowflake | Snowflake data warehouse | `pip install prefect-snowflake` |
| prefect-slack | Slack notifications | `pip install prefect-slack` |
| prefect-email | Email notifications (SMTP) | `pip install prefect-email` |
| prefect-shell | Shell commands | `pip install prefect-shell` |
| prefect-github | GitHub repos, code storage | `pip install prefect-github` |
| prefect-gitlab | GitLab repos, code storage | `pip install prefect-gitlab` |
| prefect-bitbucket | Bitbucket repos | `pip install prefect-bitbucket` |
| prefect-databricks | Databricks jobs | `pip install prefect-databricks` |
| prefect-ray | Ray distributed computing | `pip install prefect-ray` |
| prefect-dask | Dask distributed computing | `pip install prefect-dask` |

## Common Flow Templates by Industry

### Data Engineering

| Flow | Pattern | Schedule |
|------|---------|----------|
| API ingestion | fetch → validate → store | Hourly |
| Database replication | read source → transform → write target | Every 15 min |
| Data quality checks | read → validate rules → alert on failure | Hourly |
| Schema migration | backup → migrate → validate → rollback on fail | On-demand |
| Partition management | create new partitions → archive old → vacuum | Daily |

### ML/AI Operations

| Flow | Pattern | Schedule |
|------|---------|----------|
| Feature engineering | read raw → compute features → store in feature store | Hourly |
| Model training | fetch data → train → evaluate → register if better | Weekly |
| Model inference batch | load model → predict on batch → store results | Daily |
| Drift detection | compare distributions → alert if drift > threshold | Daily |
| A/B test analysis | fetch metrics → compute significance → report | Weekly |

### Web Scraping

| Flow | Pattern | Schedule |
|------|---------|----------|
| Multi-site scraper | for each site: fetch → extract → normalize → store | Every 6h |
| Price monitor | scrape prices → compare with stored → alert on change | Hourly |
| Content aggregator | scrape RSS/news → dedup → categorize → store | Every 30 min |
| Image collector | fetch items → download images → upload to S3 → update refs | After scraper |
| Sitemap crawler | fetch sitemap → discover URLs → queue for scraping | Daily |

### Business Operations

| Flow | Pattern | Schedule |
|------|---------|----------|
| Invoice generation | fetch orders → calculate totals → generate PDF → email | Daily |
| Lead scoring | fetch contacts → compute score → update CRM | Daily |
| Report generation | aggregate metrics → build report → save/email | Weekly |
| Data cleanup | find duplicates → merge → archive old → report | Weekly |
| Compliance audit | check all records → flag violations → generate report | Monthly |

### DevOps/Infrastructure

| Flow | Pattern | Schedule |
|------|---------|----------|
| Database backup | pg_dump → compress → upload to S3 → cleanup old | Daily |
| Health monitoring | check endpoints → alert if down → log results | Every 5 min |
| Log rotation | compress old logs → upload to storage → delete local | Daily |
| Certificate renewal | check expiry → renew if < 30 days → deploy → verify | Daily |
| Cost monitoring | fetch cloud bills → compare with budget → alert | Daily |

## Deployment Patterns

### Pattern A: serve() — Simple, single process

```python
if __name__ == "__main__":
    my_flow.serve(name="my-deployment", cron="0 * * * *")
```

Best for: development, single flows, simple schedules.

### Pattern B: deploy() — Work pool based

```python
if __name__ == "__main__":
    my_flow.deploy(name="my-deployment", work_pool_name="docker-pool", cron="0 * * * *")
```

Best for: production, Docker/K8s infrastructure, team environments.

### Pattern C: prefect.yaml — Declarative

```yaml
deployments:
  - name: property-pipeline
    entrypoint: flows/property_pipeline.py:property_pipeline
    work_pool:
      name: default
    schedule:
      cron: "0 */6 * * *"
    parameters:
      sites: ["mercadolibre_ve"]
      max_pages: 5
```

Best for: CI/CD, version-controlled deployment configs.

### Pattern D: API trigger — Event-driven

```python
# From n8n, Agno, or any HTTP client:
httpx.post(f"{PREFECT_API}/deployments/{id}/create_flow_run",
    json={"parameters": {"urls": ["https://..."]}})
```

Best for: on-demand flows triggered by external events.
