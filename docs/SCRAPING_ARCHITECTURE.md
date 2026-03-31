# QYNE v1 — Scraping Pipeline Architecture & Production Guide

## Architecture Overview

```
                    ┌─────────────────────────┐
                    │   property_pipeline()    │  ← Single flow, multiple sites
                    │   sites=["site_name"]    │
                    └────────┬────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │ rentahouse  │ │ century21   │ │ mercadolibre│  ← Site configs
    │ CSS listing │ │ Link listing│ │ CSS listing │
    │ + detail    │ │ + detail    │ │ (no detail) │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           ▼               ▼               ▼
    ┌─────────────────────────────────────────────┐
    │              normalize()                     │  ← Standard JSON schema
    │  Clean title, features, price, location      │
    └──────────────────┬──────────────────────────┘
                       │
              ┌────────┼────────┐
              ▼        ▼        ▼
         validate  is_duplicate  enrich
              │        │           │
              └────────┼───────────┘
                       ▼
              ┌─────────────────┐
              │  Directus store  │  ← properties collection
              │  (38 fields)     │
              └─────────────────┘
```

## Deployment Strategy (Prefect Best Practices)

### One Flow, Separate Deployments Per Site

The `property_pipeline` flow is ONE function. Each site gets its own
Prefect deployment with independent schedule, parameters, and monitoring.

```
Deployments:
├── property-rentahouse-daily     → sites=["rentahouse_ve"], max_pages=1
├── property-century21-daily      → sites=["century21_ve"], max_pages=1
├── property-mercadolibre-daily   → sites=["mercadolibre_ve"], max_pages=1
├── property-all-weekly           → sites=null (all), max_pages=5
└── property-verifier-weekly      → selector_health_check flow
```

### Why Separate Deployments (Not Separate Flows)

| Approach | Pros | Cons |
|----------|------|------|
| Separate flows per site | Full isolation | Code duplication, harder to maintain |
| **Separate deployments, same flow** | Shared code, independent schedules | Shared failure modes |
| Single deployment, all sites | Simple | One failure blocks all |

**We use separate deployments** because:
- Same normalize/validate/store code for all sites
- Each site has its own schedule (staggered hours)
- If Century21 fails, RentAHouse keeps running
- Prefect dashboard shows each site as a separate deployment
- Easy to pause one site without affecting others

### Schedule (Staggered to Avoid VPS Overload)

| Deployment | Schedule | Parameters |
|------------|----------|------------|
| property-rentahouse-daily | `0 4 * * *` (4am UTC) | sites=["rentahouse_ve"], max_pages=1 |
| property-century21-daily | `0 5 * * *` (5am UTC) | sites=["century21_ve"], max_pages=1 |
| property-verifier-weekly | `0 3 * * 0` (Sun 3am) | check_urls=true, url_sample=100 |

### Concurrency

Only ONE property pipeline runs at a time. The worker has `concurrency_limit=1`
for the default-pool. This prevents:
- Two scrapers hitting the same site simultaneously
- RAM spikes from parallel Playwright instances
- Rate limiting from concurrent requests

## Listing Modes

Each site uses one of two listing modes:

### CSS Mode (RentAHouse, MercadoLibre)

```
1. Fetch listing page
2. Extract items with JsonCssExtractionStrategy (CSS selectors)
3. For each item: fetch detail page (if scrape_details=true)
4. Normalize → Validate → Dedup → Enrich → Store
```

Best for: Sites with server-rendered HTML and consistent card structure.

### Links Mode (Century21)

```
1. Fetch listing page
2. Extract property URLs with regex pattern
3. For each URL: fetch detail page with site-specific parser
4. Normalize → Validate → Dedup → Enrich → Store
```

Best for: SPAs, WordPress sites, or sites where listing cards don't have
enough data and you need the detail page for everything.

## Phone Number Standard

All phone numbers are stored in **international format with country code**:

| Source format | Stored as | Rule |
|---------------|-----------|------|
| `wa.me/584223274689` | `584223274689` | Already international |
| `tel:04242961568` | `584242961568` | Replace leading 0 with 58 |
| `+58 414 123 4567` | `584141234567` | Strip +, spaces, dashes |
| `0414-123-4567` | `584141234567` | Replace 0 with 58, strip dashes |

The normalize function should apply this conversion. Currently RentAHouse
numbers are already international (from wa.me links). Century21 numbers
need the 0→58 conversion.

## Data Quality Checks

### Per-Scrape (Automatic)

| Check | Action |
|-------|--------|
| 0 items fetched | Critical alert in Directus events |
| Price changed | Append to price_history, update price |
| URL returns 404 | Mark status="sold", set sold_at |
| Missing required fields | Reject in validate() |

### Weekly (Selector Health Check)

| Check | Action |
|-------|--------|
| CSS selectors return 0 items | Alert: selectors may be broken |
| Sample URLs return 404 | Mark properties as sold |
| Properties not verified in 30 days | Mark as stale |

### Monthly (Manual Review)

| Check | What to look for |
|-------|-----------------|
| Title quality | Still clean? No raw HTML? |
| Phone format | All international? |
| Price categories | Correct for venta vs alquiler? |
| Duplicate rate | Cross-source matches working? |
| Feature quality | No symbols? No negatives? |

## Adding a New Site

### Step 1: Analyze the Site

```bash
# Test with Crawl4AI
docker exec qyne-prefect-worker python3 -c "
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, BrowserConfig
async def test():
    bc = BrowserConfig(headless=True, java_script_enabled=True)
    config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, delay_before_return_html=5.0)
    async with AsyncWebCrawler(config=bc) as crawler:
        result = await crawler.arun(url='https://newsite.com/listings', config=config)
        print(result.markdown[:3000])
asyncio.run(test())
"
```

Questions to answer:
1. Does the listing page load via JS or server-render?
2. Are property cards in the HTML or loaded via AJAX?
3. Does the site have pagination via URL params?
4. Does the detail page have all the data we need?
5. Where is the realtor info (name, phone, email)?
6. Where are the images (CDN URL pattern)?

### Step 2: Choose Listing Mode

- If cards are in HTML with consistent CSS classes → `listing_mode: "css"`
- If you need to extract links and scrape each detail → `listing_mode: "links"`

### Step 3: Add Config to SITE_CONFIGS

```python
"newsite_ve": {
    "base_url": "https://newsite.com/listings",
    "pagination": "?page={page}",
    "items_per_page": 20,
    "max_pages": 5,
    "country": "VE",
    "currency_default": "USD",
    "delay_seconds": 3.0,
    "scrape_details": True,
    "listing_mode": "css",  # or "links"
    "schema": { ... },      # CSS selectors (for css mode)
    "link_pattern": r"...", # Regex (for links mode)
    "detail_parser": "default",  # or custom parser name
}
```

### Step 4: Add Detail Parser (if needed)

If the site's detail page has a unique structure, add a dedicated parser:

```python
@task(retries=2, retry_delay_seconds=10)
async def fetch_detail_newsite(url: str) -> dict:
    # Parse markdown/HTML specific to this site
    ...
```

### Step 5: Test

```bash
# Test with 5 properties
python3 -c "
import asyncio, sys
sys.path.insert(0, '/app')
from flows.property_pipeline import SITE_CONFIGS, property_pipeline
SITE_CONFIGS['newsite_ve']['items_per_page'] = 5
asyncio.run(property_pipeline(sites=['newsite_ve'], max_pages=1, download_images=False))
"
```

### Step 6: Verify JSON

Check that all required fields are populated:
- title (clean, no raw HTML)
- price + currency
- operation (venta/alquiler)
- city + country
- url + source
- images (at least 1)
- realtor_name + realtor_phone (international format)

### Step 7: Register Deployment

```python
property_pipeline.to_deployment(
    name="property-newsite-daily",
    cron="0 6 * * *",
    parameters={"sites": ["newsite_ve"], "max_pages": 1},
)
```

## Error Recovery

| Error | Cause | Fix |
|-------|-------|-----|
| SignatureMismatchError | Wrong parameters sent to flow | Check deployment parameters |
| FileNotFoundError | Worker can't find flow file | Set path=/app in deployment |
| 0 items extracted | CSS selectors broken | Update selectors in SITE_CONFIGS |
| 403 Forbidden | Rate limited or blocked | Increase delay_seconds, add proxy |
| Store returns None | Directus permission denied | Add create permission for properties |
| Timeout | Page too slow to load | Increase page_timeout |

## Current Sites

| Site | Mode | Items/page | Detail parser | Status |
|------|------|-----------|---------------|--------|
| rentahouse_ve | CSS + detail | 20 | default (rentahouse) | Production |
| century21_ve | Links + detail | 100 | century21 | Production |
| mercadolibre_ve | CSS only | 48 | none | Configured, not tested |
