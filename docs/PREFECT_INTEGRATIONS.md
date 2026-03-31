# QYNE v1 — Prefect Integrations & Pipeline Production Hardening

## Prefect Integrations Catalog

Prefect integrations are Python packages that add pre-built tasks and blocks
for connecting to external services. Install with `pip install prefect-[name]`.

### Tier 1: Actively Maintained by Prefect (2026)

| Package | What it does | Key features | Relevance for QYNE |
|---------|-------------|--------------|---------------------|
| `prefect-aws` | AWS services (S3, ECS, Lambda, Secrets Manager) | S3 read/write, ECS task runs, Lambda invocations | LOW — we use Hetzner |
| `prefect-azure` | Azure services (Blob, ACI, Cosmos) | Blob storage, container instances | LOW |
| `prefect-gcp` | Google Cloud (GCS, BigQuery, Cloud Run) | BigQuery queries, GCS storage | LOW |
| `prefect-docker` | Docker container management | Run flows in containers, build images | POSSIBLE — alternative to process worker |
| `prefect-kubernetes` | Kubernetes orchestration | K8s jobs, pod management | LOW — no K8s |
| `prefect-github` | GitHub repository access | Clone repos, read files, trigger from commits | LOW |
| `prefect-gitlab` | GitLab repository access | Clone repos, CI/CD triggers | LOW |
| `prefect-bitbucket` | Bitbucket repository access | Clone repos | LOW |
| `prefect-slack` | Slack messaging | Send messages, alerts on flow completion/failure | **HIGH** — alerting |
| `prefect-email` | Email sending | SMTP email tasks, HTML templates | **HIGH** — reports |
| `prefect-redis` | Redis operations | Cache, pub/sub, rate limiting | **MEDIUM** — we have Redis |
| `prefect-shell` | Shell command execution | Run bash commands as tasks | ALREADY USED implicitly |
| `prefect-dbt` | dbt transformations | Run dbt models, test, snapshot | FUTURE — analytics |
| `prefect-sqlalchemy` | Database connectivity | SQL queries, transactions, any DB | **MEDIUM** — direct Postgres queries |
| `prefect-snowflake` | Snowflake data warehouse | Queries, bulk load | LOW |
| `prefect-dask` | Parallel computing | Distribute tasks across workers | LOW — single VPS |
| `prefect-ray` | Distributed computing | Ray cluster task execution | LOW |
| `prefect-databricks` | Spark analytics | Databricks job runs | LOW |
| `prefect-mcp` | MCP server for Prefect | Expose Prefect as MCP tool for AI agents | **HIGH** — Agno integration |
| `prefect-cloud` | Prefect Cloud deployment | Easy cloud deployment | LOW — self-hosted |

### Tier 2: Community / Third-Party

| Package | What it does | Relevance |
|---------|-------------|-----------|
| `prefect-openai` | OpenAI API tasks | POSSIBLE — LLM extraction |
| `prefect-airbyte` | Airbyte sync triggers | LOW — no Airbyte |
| `prefect-census` | Census reverse ETL syncs | LOW |
| `prefect-hightouch` | Hightouch reverse ETL | LOW |
| `prefect-monte-carlo` | Data observability | FUTURE — data quality |
| `prefect-great-expectations` | Data validation | **MEDIUM** — JSON validation |
| `prefect-duckdb` | DuckDB analytics | POSSIBLE — local analytics |
| `prefect-openmetadata` | Metadata management | LOW |
| `prefect-twitter` | Twitter API | LOW |
| `prefect-monday` | Monday.com tasks | LOW |
| `prefect-hex` | Hex notebook runs | LOW |
| `langchain-prefect` | LangChain orchestration | LOW — we use Agno |

### Recommended for QYNE (Priority Order)

1. **prefect-slack** — Alert when scraping fails, daily summary
2. **prefect-email** — Weekly property reports, error notifications
3. **prefect-mcp** — Let Agno agents interact with Prefect directly via MCP
4. **prefect-redis** — Rate limiting, caching scraped URLs
5. **prefect-sqlalchemy** — Direct Postgres queries for analytics
6. **prefect-great-expectations** — JSON schema validation for properties

## Pipeline Production Hardening

### Current State vs Production Grade

| Feature | Current | Production Grade | Priority |
|---------|---------|-----------------|----------|
| Retries | 2-3 per task | OK | DONE |
| Retry delay | Fixed (10-30s) | Exponential backoff | MEDIUM |
| Circuit breaker | None | Stop after N consecutive failures | **HIGH** |
| Rate limiting | Fixed delay (3s) | Adaptive per-domain | MEDIUM |
| Logging | logger.info/error | Structured JSON logs | LOW |
| Metrics | None | Duration per task, items/sec | MEDIUM |
| Notifications | Directus events only | Slack + Directus | **HIGH** |
| Deployments | Manual API calls | Registered in code | **HIGH** |
| Tests | None | Unit tests for normalize | MEDIUM |
| JSON validation | validate() basic check | Schema validation | **HIGH** |
| Phone format | Mixed (local + international) | All international | MEDIUM |

### Circuit Breaker Pattern

When a site fails repeatedly, stop trying and alert:

```python
MAX_CONSECUTIVE_FAILURES = 3

@task
def check_circuit_breaker(site_name: str) -> bool:
    """Check if site has too many recent failures. Returns True if OK to proceed."""
    # Query Directus events for recent scraper_alert events
    resp = httpx.get(
        f"{DIRECTUS_URL}/items/events",
        params={
            "filter[type][_eq]": "scraper_alert",
            "filter[payload][_contains]": site_name,
            "sort": "-date_created",
            "limit": MAX_CONSECUTIVE_FAILURES,
        },
        headers=HEADERS,
    )
    alerts = resp.json().get("data", [])
    if len(alerts) >= MAX_CONSECUTIVE_FAILURES:
        logger.error(f"Circuit breaker OPEN for {site_name}: {len(alerts)} consecutive failures")
        return False
    return True
```

### JSON Completeness Validation

A separate flow that audits properties in Directus:

```python
@flow(name="Property Data Quality Audit")
async def property_quality_audit():
    """Check all properties for missing required fields."""
    required = ["title", "price", "city", "url", "source", "images"]
    recommended = ["bedrooms", "bathrooms", "area_m2", "realtor_name", "realtor_phone", "operation"]

    # Query properties missing required fields
    for field in required:
        resp = httpx.get(
            f"{DIRECTUS_URL}/items/properties",
            params={"filter[{field}][_null]": True, "aggregate[count]": "id"},
            headers=HEADERS,
        )
        count = resp.json()["data"][0]["count"]["id"]
        if count > 0:
            logger.warning(f"QUALITY: {count} properties missing required field '{field}'")

    # Check completeness score
    for field in recommended:
        # Count nulls
        # Log percentage complete
        pass
```

This is the professional approach: a **separate audit flow** that runs weekly
and reports data quality metrics. It doesn't block the scraping pipeline —
it runs independently and creates reports.

### Why Separate Audit Flow (Not Inline Validation)

| Approach | Pros | Cons |
|----------|------|------|
| Inline validation (in pipeline) | Immediate feedback | Blocks pipeline, can't fix retroactively |
| **Separate audit flow** | Non-blocking, covers all data, historical | Delayed feedback |
| Both | Best coverage | More complexity |

**Recommendation**: Keep basic `validate()` in the pipeline (reject truly broken data)
AND run a weekly audit flow for completeness reporting.

### Unregistered Deployments

Current state: deployments were created via API calls, not in code.
If the Prefect server restarts, they may be lost.

**Fix**: Register deployments in `register_deployments.py`:

```python
from flows.property_pipeline import property_pipeline
from flows.selector_health_check import selector_health_check

if __name__ == "__main__":
    # Property pipelines — one deployment per site
    property_pipeline.to_deployment(
        name="property-rentahouse-daily",
        cron="0 4 * * *",
        parameters={"sites": ["rentahouse_ve"], "max_pages": 1},
        work_pool_name="default-pool",
    )
    property_pipeline.to_deployment(
        name="property-century21-daily",
        cron="0 5 * * *",
        parameters={"sites": ["century21_ve"], "max_pages": 1},
        work_pool_name="default-pool",
    )

    # Health check
    selector_health_check.to_deployment(
        name="selector-health-weekly",
        cron="0 3 * * 0",
        parameters={"check_urls": True, "url_sample": 100},
        work_pool_name="default-pool",
    )
```

### Normalize Resilience

The normalize function should NEVER crash. Every field extraction
should be wrapped in try/except with a default value:

```python
# BAD: crashes if dormitorios is not a digit
bedrooms = int(raw["dormitorios"])

# GOOD: returns None on any error
try:
    bedrooms = int(raw["dormitorios"]) if raw.get("dormitorios") else None
except (ValueError, TypeError):
    bedrooms = None
```

Current normalize has some unprotected conversions that could crash
on unexpected data. These should be hardened.

### Phone Number Standardization

All phones should be international format before storing:

```python
def standardize_phone(phone: str, country_code: str = "58") -> str:
    """Convert any phone format to international: 58XXXXXXXXXX"""
    if not phone:
        return ""
    digits = re.sub(r"[^\d]", "", phone)
    if digits.startswith("0") and len(digits) == 11:
        return country_code + digits[1:]  # 0414... → 58414...
    if digits.startswith(country_code):
        return digits
    if len(digits) == 10:
        return country_code + digits
    return digits
```

## Implementation Roadmap

### Phase 1: Critical (This Week)

1. Register deployments in code (not just API)
2. Add circuit breaker to pipeline
3. Standardize phone numbers in normalize
4. Harden normalize with try/except on all conversions

### Phase 2: Important (Next Week)

5. Install prefect-slack, add failure notifications
6. Create property quality audit flow
7. Add exponential backoff to retries
8. Unit tests for normalize function

### Phase 3: Nice to Have (This Month)

9. Install prefect-email for weekly reports
10. Explore prefect-mcp for Agno direct integration
11. Add structured logging (JSON format)
12. Add duration metrics per task
