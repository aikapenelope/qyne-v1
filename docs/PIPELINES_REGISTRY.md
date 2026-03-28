# QYNE v1 — Prefect Pipelines & Flows Registry

## Pipelines (Multi-Stage)

### 1. Property Pipeline (`property_pipeline.py`)

**Purpose**: Scrape real estate listings from multiple sites, process, and store as PWA-ready JSON.

**Trigger**: Chat ("Scrapea propiedades de MercadoLibre") or scheduled (every 6h).

**Stages**:
```
Stage 1: FETCH + EXTRACT    Crawl4AI + CSS schema per site
Stage 2: NORMALIZE          Clean prices, currencies, locations, URLs
Stage 3: VALIDATE           Required fields, type checks, range checks
Stage 4: DEDUP              URL uniqueness check against Directus
Stage 5: ENRICH             price_per_m2, price_category, property_type, features
Stage 6: STORE              Directus properties collection (PWA-ready JSON)
Stage 7: DOWNLOAD IMAGES    External URLs → RustFS properties/{id}/{hash}.jpg
Stage 8: UPDATE             Replace external URLs with RustFS URLs, status="ready"
```

**Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| sites | list[str] | all configured | Site names from SITE_CONFIGS |
| max_pages | int | 5 per site | Pages to scrape per site |
| download_images | bool | True | Whether to download images to RustFS |

**Site Configs Available**:
| Site | Country | Currency | CSS Schema |
|------|---------|----------|------------|
| mercadolibre_ve | VE | USD | li.ui-search-layout__item |
| (add more) | | | |

**Output**: Directus `properties` collection
```json
{
  "id": 42,
  "title": "Apartamento en Caracas",
  "price": 85000,
  "currency": "USD",
  "price_per_m2": 708.33,
  "price_category": "mid",
  "location": "Caracas, Miranda",
  "city": "Caracas",
  "country": "VE",
  "bedrooms": 3,
  "bathrooms": 2,
  "area_m2": 120,
  "property_type": "apartment",
  "features": ["piscina", "estacionamiento"],
  "images": [
    {"url": "http://rustfs:9000/properties/42/abc123.jpg", "alt": "Apartamento Caracas", "order": 0, "source": "rustfs", "size_bytes": 245000}
  ],
  "url": "https://inmuebles.mercadolibre.com.ve/...",
  "source": "mercadolibre_ve",
  "status": "ready"
}
```

**Monitoring**: Logs to Directus `events` with type="property_pipeline".

---

### 2. Website Crawler (`website_crawler.py`)

**Purpose**: Deep crawl an entire website, convert to clean markdown, classify by topic, index for RAG.

**Trigger**: Chat ("Crawlea la documentacion de agno.com") or on-demand.

**Stages**:
```
Stage 1: DISCOVER       BFS from start URL, follow internal links
Stage 2: FETCH          Crawl4AI renders JS, extracts fit_markdown
Stage 3: CHUNK          Split by headers, max 500 tokens per chunk
Stage 4: CLASSIFY       Detect topic from URL path + content (27 keywords)
Stage 5: DEDUP          URL uniqueness check against Directus
Stage 6: STORE          Directus documents collection with topic classification
Stage 7: INDEX          Each chunk → Voyage AI embeddings → LanceDB
```

**Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| url | str | required | Starting URL to crawl |
| max_pages | int | 50 | Maximum pages to discover |
| max_depth | int | 3 | Maximum link depth from start |
| include_paths | list[str] | None | Only crawl URLs containing these |
| exclude_paths | list[str] | None | Skip URLs containing these |
| index_in_knowledge | bool | True | Index chunks in LanceDB |
| max_chunk_tokens | int | 500 | Max tokens per RAG chunk |

**Output**: Directus `documents` collection + LanceDB chunks
```
Directus:
  title: "Agents Overview"
  content: "# Agents\n\nAgents are AI programs where..."  (full markdown)
  source_file: "https://docs.agno.com/agents"
  status: "crawled:Agents:agents"

LanceDB (per chunk):
  text: "Agents are AI programs where a language model..."
  metadata: {title, source, chunk_index, topic: "Agents", category: "agents", breadcrumb: "agents"}
```

**Monitoring**: Logs to Directus `events` with type="website_crawl".

---

## Individual Flows

### Data Operations

| Flow | File | Schedule | Input | Output | Description |
|------|------|----------|-------|--------|-------------|
| Data Sync | `data_sync.py` | Hourly | source/target collection | Directus | Sync data between collections with field mapping |
| Data Cleanup | `data_cleanup.py` | Sun 2am | archive_days (90) | Directus events (report) | Find duplicates, old data, test records. Report only, no delete |
| Dedup Merger | `dedup_merger.py` | On-demand | dry_run (True) | Directus contacts | Find duplicate contacts by email, merge intelligently |
| Data Enricher | `data_enricher.py` | Daily | collection, filter | Directus (updated) | Add computed fields: email domain classification, lead score boost |
| Export CSV | `export_csv.py` | On-demand | collection, fields | RustFS exports/ | Export any collection to CSV in RustFS |
| Import CSV | `import_csv.py` | On-demand | bucket, filename, collection | Directus | Import CSV from RustFS into any collection |

### Document Processing

| Flow | File | Schedule | Input | Output | Description |
|------|------|----------|-------|--------|-------------|
| ETL Documents | `etl_documents.py` | On-demand | file_paths | Directus documents + LanceDB | Docling parse PDF/DOCX → text + embeddings |
| Knowledge Indexer | `knowledge_indexer.py` | On-demand | - | LanceDB | Index pending documents (status=pending) into LanceDB |

### Monitoring & Reporting

| Flow | File | Schedule | Input | Output | Description |
|------|------|----------|-------|--------|-------------|
| Health Check | `health_check.py` | Every 5 min | - | Directus events + tasks | Check all services, create alert task if down |
| Weekly Report | `report_generator.py` | Mon 8am | days_back (7) | Directus events | Aggregate metrics: contacts, tickets, conversations |
| Daily Digest | `email_digest.py` | Daily 8am | hours_back (24) | Directus events | Summary of recent contacts, tickets, tasks |
| Lead Scorer | `lead_scorer.py` | Daily 6am | - | Directus contacts | Recalculate lead scores from activity and recency |
| Sentiment Analyzer | `sentiment_analyzer.py` | Daily | limit (100) | Directus conversations | Keyword-based sentiment scoring (no LLM) |

### Infrastructure

| Flow | File | Schedule | Input | Output | Description |
|------|------|----------|-------|--------|-------------|
| Database Backup | `database_backup.py` | Daily 3am | databases, bucket | RustFS backups/ | pg_dump directus_db + prefect_db → gzip → RustFS |
| Scraper LATAM | `scraper_latam.py` | Every 6h | urls, collection | Directus scraped_data | Generic BeautifulSoup scraper (legacy, use property_pipeline instead) |

---

## Flow Configuration Standards

Every flow follows these production defaults:

```python
@flow(
    name="Human Readable Name",
    log_prints=True,
    retries=1,
    retry_delay_seconds=60,
    timeout_seconds=3600,
)

@task(
    retries=3,
    retry_delay_seconds=[10, 30, 60],
    timeout_seconds=300,
    log_prints=True,
)
```

## How to Add a New Site to Property Pipeline

1. Inspect the site HTML structure (browser DevTools)
2. Define CSS selectors for each field
3. Add config to `SITE_CONFIGS` in `property_pipeline.py`:
```python
"new_site": {
    "base_url": "https://newsite.com/properties/",
    "pagination": "?page={offset}",
    "items_per_page": 20,
    "max_pages": 5,
    "country": "CO",
    "currency_default": "COP",
    "schema": {
        "name": "New Site",
        "baseSelector": "div.listing-card",
        "fields": [
            {"name": "title", "selector": "h3.title", "type": "text"},
            {"name": "price_raw", "selector": "span.price", "type": "text"},
            ...
        ],
    },
}
```
4. Deploy and test: `property_pipeline(sites=["new_site"], max_pages=1)`

## How to Crawl a New Website

```python
# From chat:
"Crawlea docs.example.com, solo la seccion de API"

# Automation Agent triggers:
website_crawler(
    url="https://docs.example.com",
    max_pages=100,
    include_paths=["/api/"],
    exclude_paths=["/blog/", "/changelog/"],
)
```
