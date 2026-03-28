# QYNE v1 — Data Pipeline Architecture: Extraction, Storage, Consumption

## Token Economics: Database vs Internet

| Operation | Tokens consumed | Latency | Data quality |
|-----------|----------------|---------|-------------|
| Agent searches internet (DuckDuckGo) | 5,000-15,000 per query | 5-15s | Snippets, may be outdated |
| Agent reads Directus via MCP | 500-2,000 per query | 0.5-2s | Exact, structured, current |
| Agent reads Directus via REST tool | 200-500 per query | 0.3-1s | Exact, structured, current |
| Prefect scrapes with Crawl4AI | 0 tokens (no LLM) | 2-30s per page | Full page, images, structured |
| Prefect scrapes with LLM extraction | 1,000-3,000 per page | 10-30s per page | Interpreted, flexible |

**Rule**: Scrape once with Prefect (0 tokens), store in Directus, query many times
with agents (500 tokens each). One scrape of 50 pages saves 250,000+ tokens
compared to 50 agent web searches.

## How Crawl4AI Structures Data

Crawl4AI has two extraction modes:

### Mode 1: CSS Schema (no LLM, free, instant)

Define CSS selectors per site. Best for consistent HTML structures like
MercadoLibre, Zillow, real estate portals.

```python
# Schema for MercadoLibre property listings
schema = {
    "name": "MercadoLibre Properties",
    "baseSelector": "li.ui-search-layout__item",
    "fields": [
        {"name": "title", "selector": "h2.ui-search-item__title", "type": "text"},
        {"name": "price", "selector": "span.andes-money-amount__fraction", "type": "text"},
        {"name": "currency", "selector": "span.andes-money-amount__currency-symbol", "type": "text"},
        {"name": "location", "selector": "span.ui-search-item__location", "type": "text"},
        {"name": "url", "selector": "a.ui-search-link", "type": "attribute", "attribute": "href"},
        {"name": "image", "selector": "img.ui-search-result-image__element", "type": "attribute", "attribute": "src"},
        {"name": "area", "selector": "li.ui-search-card-attributes__attribute", "type": "text"},
    ]
}
```

Result: structured JSON array, one object per listing, ready for Directus.

### Mode 2: LLM Extraction (costs tokens, flexible)

For pages with inconsistent structure. The LLM interprets the page and
extracts data matching your Pydantic schema.

```python
from pydantic import BaseModel

class Property(BaseModel):
    title: str
    price: float
    currency: str
    location: str
    bedrooms: int
    bathrooms: int
    area_m2: float
    description: str
    images: list[str]
    url: str

strategy = LLMExtractionStrategy(
    llm_config=LLMConfig(provider="groq/llama-3.1-8b-instant"),
    schema=Property.model_json_schema(),
    extraction_type="schema",
    instruction="Extract all property listings from this page.",
)
```

### Which to use?

| Site type | Strategy | Cost |
|-----------|----------|------|
| MercadoLibre (consistent HTML) | CSS Schema | Free |
| Random blog with property data | LLM Extraction | ~1K tokens/page |
| PDF property brochure | Docling + LLM | ~2K tokens/doc |
| API with JSON response | Direct httpx (no Crawl4AI) | Free |

## Data Flow: Scrape → Store → Consume

```
SCRAPE (Prefect + Crawl4AI)
    │
    │ Structured JSON per item
    ▼
STORE (Directus)
    │
    ├── scraped_data: raw scraped items
    ├── properties: cleaned property listings (if you create this collection)
    ├── documents: parsed document text
    └── events: scrape logs and metadata
    │
    ▼
CONSUME (Agents via MCP or REST)
    │
    ├── Dash: "cuantas propiedades hay en Caracas?" → reads scraped_data
    ├── Support: "que propiedades tenemos?" → reads properties
    ├── Research: compares with web data → reads scraped_data + web search
    └── External API: your apps read from Directus REST API
```

## Prefect Workers: Data Processing Toolkit

### What we have (10 flows)

| Flow | Input | Processing | Output |
|------|-------|-----------|--------|
| scraper_latam | URLs | Crawl4AI + BeautifulSoup | Directus scraped_data |
| etl_documents | File paths | Docling parse | Directus documents + LanceDB |
| database_backup | - | pg_dump + gzip | RustFS |
| data_sync | Collection names | Read + transform + write | Directus |
| report_generator | - | Aggregate Directus data | Directus events |
| email_digest | - | Summarize activity | Directus events |
| knowledge_indexer | - | Voyage AI embeddings | LanceDB |
| health_check | - | HTTP checks | Directus events + tasks |
| data_cleanup | - | Find duplicates | Directus events (report) |
| lead_scorer | - | Calculate scores | Directus contacts |

### What we should add for production

| Flow | Purpose | Input | Output |
|------|---------|-------|--------|
| **property_scraper** | Scrape real estate sites with CSS schemas | Site configs | Directus properties |
| **image_downloader** | Download scraped image URLs to RustFS | scraped_data items | RustFS + Directus file refs |
| **data_enricher** | Enrich contacts with web data (LinkedIn, domain) | Directus contacts | Directus contacts (updated) |
| **export_csv** | Export any collection to CSV for external use | Collection name | RustFS CSV file |
| **import_csv** | Import CSV data into any collection | RustFS CSV path | Directus collection |
| **dedup_merger** | Merge duplicate contacts intelligently | Directus contacts | Directus contacts (merged) |
| **sentiment_analyzer** | Analyze conversation sentiment (batch) | Directus conversations | Directus conversations (updated) |
| **cache_warmer** | Pre-compute common queries for Dash | - | Redis cache |

## Property Scraper: Multi-Site Architecture

For scraping 3 different property sites, create one flow with site-specific configs:

```python
SITE_CONFIGS = {
    "mercadolibre_ve": {
        "base_url": "https://inmuebles.mercadolibre.com.ve",
        "schema": {
            "name": "MercadoLibre VE",
            "baseSelector": "li.ui-search-layout__item",
            "fields": [
                {"name": "title", "selector": "h2.ui-search-item__title", "type": "text"},
                {"name": "price", "selector": "span.andes-money-amount__fraction", "type": "text"},
                {"name": "location", "selector": "span.ui-search-item__location", "type": "text"},
                {"name": "url", "selector": "a.ui-search-link", "type": "attribute", "attribute": "href"},
                {"name": "image", "selector": "img", "type": "attribute", "attribute": "src"},
            ]
        },
        "pagination": "?Desde={offset}",
        "max_pages": 10,
    },
    "site_b": {
        "base_url": "https://example-realestate.com",
        "schema": { ... },  # Different CSS selectors per site
    },
    "site_c": {
        "base_url": "https://another-site.com",
        "schema": { ... },
    },
}

@flow(name="Property Scraper")
async def property_scraper(sites: list[str] | None = None):
    sites = sites or list(SITE_CONFIGS.keys())
    for site_name in sites:
        config = SITE_CONFIGS[site_name]
        for page in range(config["max_pages"]):
            url = config["base_url"] + config["pagination"].format(offset=page * 50)
            items = await scrape_with_schema(url, config["schema"])
            save_to_directus(items, collection="properties", source=site_name)
```

### Image Handling

Crawl4AI extracts image URLs, not image files. The flow:

1. Scraper extracts `image: "https://mlstatic.com/photo123.jpg"`
2. Saves URL in Directus `properties.images` (JSON array of URLs)
3. Separate `image_downloader` flow downloads images to RustFS
4. Updates Directus item with RustFS URLs (permanent, no hotlinking)

```python
@flow(name="Image Downloader")
def download_images():
    # Fetch properties with external image URLs
    items = fetch_directus("properties", filter="images_downloaded=false")
    for item in items:
        local_urls = []
        for img_url in item["images"]:
            # Download to RustFS
            filename = upload_to_rustfs(img_url, bucket="property-images")
            local_urls.append(f"http://rustfs:9000/property-images/{filename}")
        # Update Directus with permanent URLs
        update_directus(item["id"], {"images": local_urls, "images_downloaded": True})
```

## Making Data Available as MCP

Once data is in Directus, agents access it via the Directus MCP server
(`@directus/content-mcp`). This means:

- Any new collection you create is instantly available to agents
- No code changes needed — MCP auto-discovers collections
- Agents can filter, sort, paginate, and aggregate via MCP tools
- The MCP server uses the agent's token (read-only, no delete)

For external consumption (your other apps, services):

- Directus REST API: `GET /items/properties?filter[location][_contains]=Caracas`
- Directus GraphQL: Same data, different query format
- Export flows: CSV/JSON exports to RustFS for batch processing

## Data Quality Rules

1. **Schema per site**: Every scraper has a defined CSS schema. No unstructured dumps.
2. **Dedup on insert**: Check URL uniqueness before saving to avoid duplicates.
3. **Source tracking**: Every item has `source` field (which site/flow created it).
4. **Timestamps**: `date_created` and `date_updated` on every item (Directus automatic).
5. **Status workflow**: `scraped` → `verified` → `published` (manual or automated).
6. **Image persistence**: Download images to RustFS, don't hotlink external URLs.
7. **Batch sizes**: Max 100 items per Directus API call to avoid timeouts.
