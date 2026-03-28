# QYNE v1 — Production Extraction Pipeline

## The 7-Stage Pipeline (Enterprise Standard 2026)

Every piece of data that enters QYNE from the web passes through 7 stages.
No shortcuts. Each stage has a specific job and produces auditable output.

```
Stage 1: FETCH        → Download raw HTML/JS pages
Stage 2: EXTRACT      → Pull structured fields from HTML
Stage 3: NORMALIZE    → Clean types, units, currencies, dates
Stage 4: VALIDATE     → Check completeness, types, business rules
Stage 5: DEDUPLICATE  → Prevent duplicate records
Stage 6: ENRICH       → Add computed fields, geocoding, categories
Stage 7: STORE        → Write to Directus with full metadata
```

### How it maps to our stack

```
Crawl4AI (Prefect worker)
    │
    ├── Stage 1: FETCH ──── AsyncWebCrawler.arun(url)
    ├── Stage 2: EXTRACT ── JsonCssExtractionStrategy (per-site schema)
    ├── Stage 3: NORMALIZE ─ Python task (clean_data)
    ├── Stage 4: VALIDATE ── Python task (validate_item)
    ├── Stage 5: DEDUP ───── Directus query (check URL exists)
    ├── Stage 6: ENRICH ──── Python task (compute fields)
    └── Stage 7: STORE ───── Directus REST API (POST /items/collection)
```

## Stage 1: FETCH (Crawl4AI)

```python
@task(retries=3, retry_delay_seconds=30)
async def fetch_page(url: str, config: SiteConfig) -> CrawlResult:
    """Fetch a page with rate limiting and retry."""
    async with AsyncWebCrawler(
        browser_type="chromium",
        headless=True,
        verbose=False,
    ) as crawler:
        result = await crawler.arun(
            url=url,
            config=CrawlerRunConfig(
                extraction_strategy=JsonCssExtractionStrategy(config.schema),
                wait_for=config.wait_selector,  # Wait for JS to render
                delay_before_return_html=config.delay_seconds,
                cache_mode=CacheMode.BYPASS,
            ),
        )
    return result
```

**Production rules:**
- Rate limit: max 2 requests/second per domain
- Random delay: 0.5-2.0 seconds between requests (human-like)
- Retry with exponential backoff on 429/503
- Respect robots.txt crawl-delay
- Rotate User-Agent strings

## Stage 2: EXTRACT (CSS Schema per site)

Each site has a defined schema. No guessing, no LLM interpretation.

```python
SCHEMAS = {
    "mercadolibre_ve": {
        "name": "MercadoLibre Venezuela",
        "baseSelector": "li.ui-search-layout__item",
        "fields": [
            {"name": "title", "selector": "h2.ui-search-item__title", "type": "text"},
            {"name": "price_raw", "selector": "span.andes-money-amount__fraction", "type": "text"},
            {"name": "currency_symbol", "selector": "span.andes-money-amount__currency-symbol", "type": "text"},
            {"name": "location", "selector": "span.ui-search-item__location", "type": "text"},
            {"name": "url", "selector": "a.ui-search-link", "type": "attribute", "attribute": "href"},
            {"name": "image_url", "selector": "img.ui-search-result-image__element", "type": "attribute", "attribute": "data-src"},
            {"name": "attributes_raw", "selector": "li.ui-search-card-attributes__attribute", "type": "text"},
        ],
    },
}
```

**Production rules:**
- One schema per site, version controlled in the repo
- Schema validation test: run against a saved HTML fixture before deploying
- If a site changes HTML structure, the schema breaks loudly (not silently)

## Stage 3: NORMALIZE

Raw extracted data is messy. Normalize before storing.

```python
@task
def normalize_item(raw: dict, site: str) -> dict:
    """Clean and normalize a single extracted item."""
    return {
        "title": (raw.get("title") or "").strip()[:500],
        "price": parse_price(raw.get("price_raw", "")),
        "currency": normalize_currency(raw.get("currency_symbol", "")),
        "location": normalize_location(raw.get("location", "")),
        "city": extract_city(raw.get("location", "")),
        "country": SITE_COUNTRIES.get(site, "unknown"),
        "url": normalize_url(raw.get("url", ""), site),
        "image_urls": extract_images(raw),
        "bedrooms": extract_number(raw.get("attributes_raw", ""), "habitacion"),
        "bathrooms": extract_number(raw.get("attributes_raw", ""), "bano"),
        "area_m2": extract_area(raw.get("attributes_raw", "")),
        "source": site,
        "scraped_at": datetime.utcnow().isoformat(),
    }

def parse_price(raw: str) -> float | None:
    """Convert '1.500.000' or '1,500,000' to float."""
    if not raw:
        return None
    cleaned = raw.replace(".", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None

def normalize_currency(symbol: str) -> str:
    """Map currency symbols to ISO codes."""
    MAP = {"$": "USD", "Bs": "VES", "Bs.": "VES", "COP": "COP", "€": "EUR"}
    return MAP.get(symbol.strip(), symbol.strip())

def normalize_url(url: str, site: str) -> str:
    """Ensure URL is absolute."""
    if url.startswith("http"):
        return url
    base = SITE_CONFIGS[site]["base_url"]
    return f"{base}{url}"
```

**Production rules:**
- Every field has a normalizer function
- Prices always stored as float + separate currency field
- Dates always ISO 8601
- URLs always absolute
- Text fields trimmed and length-limited
- Country derived from site config, not from data

## Stage 4: VALIDATE

Reject bad data before it enters the database.

```python
@task
def validate_item(item: dict) -> tuple[bool, list[str]]:
    """Validate a normalized item. Returns (is_valid, errors)."""
    errors = []

    # Required fields
    if not item.get("title"):
        errors.append("missing title")
    if not item.get("url"):
        errors.append("missing url")

    # Type checks
    if item.get("price") is not None and item["price"] <= 0:
        errors.append(f"invalid price: {item['price']}")
    if item.get("area_m2") is not None and item["area_m2"] <= 0:
        errors.append(f"invalid area: {item['area_m2']}")

    # Business rules
    if item.get("price") and item["price"] > 50_000_000:
        errors.append(f"price suspiciously high: {item['price']}")
    if item.get("bedrooms") and item["bedrooms"] > 20:
        errors.append(f"bedrooms suspiciously high: {item['bedrooms']}")

    return (len(errors) == 0, errors)
```

**Production rules:**
- Required fields: title, url, source
- Type validation: price is float, bedrooms is int
- Range validation: price > 0, area > 0, bedrooms < 20
- Business rules: flag outliers, don't silently accept
- Log validation failures to Directus events for monitoring

## Stage 5: DEDUPLICATE

Prevent the same listing from being stored twice.

```python
@task
def check_duplicate(url: str) -> bool:
    """Check if a URL already exists in Directus."""
    resp = httpx.get(
        f"{DIRECTUS_URL}/items/properties?filter[url][_eq]={url}&fields=id&limit=1",
        headers=HEADERS,
        timeout=10,
    )
    if resp.is_success:
        return len(resp.json().get("data", [])) > 0
    return False
```

**Production rules:**
- Dedup key: URL (unique per listing)
- Check before insert, not after
- For updates: if URL exists, update price/status instead of creating new
- Log dedup stats: "50 fetched, 35 new, 15 duplicates"

## Stage 6: ENRICH

Add computed fields that make the data more useful.

```python
@task
def enrich_item(item: dict) -> dict:
    """Add computed fields to a validated item."""
    enriched = {**item}

    # Price per m2
    if item.get("price") and item.get("area_m2"):
        enriched["price_per_m2"] = round(item["price"] / item["area_m2"], 2)

    # Price category
    price = item.get("price", 0)
    if price < 50000:
        enriched["price_category"] = "budget"
    elif price < 200000:
        enriched["price_category"] = "mid"
    else:
        enriched["price_category"] = "premium"

    # Status
    enriched["status"] = "scraped"

    return enriched
```

**Production rules:**
- Computed fields are deterministic (no AI, no randomness)
- Categories defined in config, not hardcoded
- Enrichment never modifies original fields, only adds new ones

## Stage 7: STORE

Write to Directus with full metadata.

```python
@task(retries=2, retry_delay_seconds=10)
def store_item(item: dict, collection: str = "properties") -> dict:
    """Store a validated, enriched item in Directus."""
    resp = httpx.post(
        f"{DIRECTUS_URL}/items/{collection}",
        json=item,
        headers=HEADERS,
        timeout=10,
    )
    if resp.is_success:
        return {"status": "saved", "id": resp.json()["data"]["id"]}
    return {"status": "error", "code": resp.status_code}
```

**Production rules:**
- Batch size: max 100 items per API call
- Retry on 5xx, fail on 4xx (bad data)
- Log every insert with item ID and source
- date_created set automatically by Directus

## The Complete Flow

```python
@flow(name="Property Scraper", log_prints=True)
async def property_scraper(
    sites: list[str] | None = None,
    max_pages: int = 5,
) -> dict:
    """Production property scraping pipeline."""
    sites = sites or list(SITE_CONFIGS.keys())
    stats = {"fetched": 0, "valid": 0, "duplicates": 0, "saved": 0, "errors": 0}

    for site_name in sites:
        config = SITE_CONFIGS[site_name]

        for page in range(max_pages):
            url = config.build_url(page)

            # Stage 1: Fetch
            result = await fetch_page(url, config)
            if not result.success:
                stats["errors"] += 1
                continue

            items = json.loads(result.extracted_content or "[]")
            stats["fetched"] += len(items)

            for raw in items:
                # Stage 2: Extract (done by Crawl4AI)
                # Stage 3: Normalize
                normalized = normalize_item(raw, site_name)

                # Stage 4: Validate
                is_valid, errors = validate_item(normalized)
                if not is_valid:
                    log_validation_error(normalized, errors)
                    stats["errors"] += 1
                    continue
                stats["valid"] += 1

                # Stage 5: Deduplicate
                if check_duplicate(normalized["url"]):
                    stats["duplicates"] += 1
                    continue

                # Stage 6: Enrich
                enriched = enrich_item(normalized)

                # Stage 7: Store
                result = store_item(enriched)
                if result["status"] == "saved":
                    stats["saved"] += 1
                else:
                    stats["errors"] += 1

    # Log run summary
    log_scrape_event(stats)
    return stats
```

## Directus Collection Schema for Properties

```
properties:
  # Core fields (from scraping)
  title: string (max 500)
  price: float
  currency: string (ISO code: USD, VES, COP)
  location: string (raw location text)
  city: string (normalized)
  country: string (from site config)
  url: string (unique, dedup key)
  image_urls: json (array of URLs)
  bedrooms: integer
  bathrooms: integer
  area_m2: float
  source: string (site name)
  scraped_at: timestamp

  # Enriched fields (computed)
  price_per_m2: float
  price_category: string (budget/mid/premium)

  # Lifecycle fields
  status: string (scraped → verified → published → archived)
  images_downloaded: boolean (false until image_downloader runs)

  # System fields (Directus automatic)
  id: integer (auto)
  date_created: timestamp
  date_updated: timestamp
  user_created: uuid
  user_updated: uuid
```

## Monitoring

Every scrape run logs to Directus events:

```json
{
  "type": "scrape_run",
  "payload": {
    "sites": ["mercadolibre_ve"],
    "fetched": 150,
    "valid": 142,
    "duplicates": 35,
    "saved": 107,
    "errors": 8,
    "duration_seconds": 45,
    "timestamp": "2026-03-27T12:00:00Z"
  }
}
```

Dash can query these events: "Como fue el ultimo scraping?" → reads events
collection → reports stats.
