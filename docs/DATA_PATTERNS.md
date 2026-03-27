# QYNE v1 — Data Patterns Guide

## Directus as Source of Truth

### Automatic Fields
Every Directus collection automatically includes system fields:
- `id` — Auto-increment primary key
- `date_created` — Timestamp when item was created
- `date_updated` — Timestamp when item was last modified
- `user_created` — Who created the item
- `user_updated` — Who last modified the item

These enable sorting by date, audit trails, and filtering by time range.

### Querying Patterns

```bash
# Most recent first
GET /items/contacts?sort=-date_created

# Filter by date range
GET /items/conversations?filter[date_created][_gte]=2026-03-01

# Filter by product/sector
GET /items/tickets?filter[product][_eq]=whabi&filter[status][_eq]=open

# Paginate (never load all)
GET /items/scraped_data?limit=100&offset=0&sort=-date_created

# Search across text fields
GET /items/documents?search=contrato

# Aggregate
GET /items/tickets?aggregate[count]=id&groupBy[]=product&groupBy[]=status
```

### Audit Trail
Directus maintains a complete audit log in `directus_activity` (internal table).
Every create, update, delete is recorded with user, timestamp, and changes.
Visible in Directus Admin under Settings > Activity.

## High-Volume Data Patterns

### Chat Logs (conversations collection)
- Each message = 1 item in `conversations`
- Fields: channel, direction, raw_message, agent_response, intent, sentiment
- Sort by `-date_created` for chronological order
- Filter by `channel` (whatsapp, web, email) or `agent_name`
- For high volume (>10K/day): consider PostgreSQL partitioning by month

### Scraping Results (scraped_data collection)
- Each scraped page = 1 item
- Fields: title, url, content, source, date_created (automatic)
- Deduplicate by URL before inserting
- Archive old data (>90 days) via Prefect flow

### Document Ingestion (documents collection)
- Each processed document = 1 item with full text
- Embeddings stored separately in LanceDB (not in Directus)
- Large documents: store full text in Directus, summary in a separate field

## Scraping Properties with Images

### Pattern: Real Estate Listings → Directus + RustFS

```python
from crawl4ai import AsyncWebCrawler
import httpx

@task
async def scrape_property(url: str) -> dict:
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)

    # Extract structured data from markdown
    return {
        "title": result.metadata.get("title", ""),
        "description": result.markdown[:10000],
        "images": [img["src"] for img in result.media.get("images", [])],
        "url": url,
        "source": "crawl4ai",
    }

@task
def save_property(prop: dict):
    """Save to Directus as structured JSON."""
    # Save property data
    r = httpx.post(f"{DIRECTUS_URL}/items/properties", json={
        "title": prop["title"],
        "description": prop["description"],
        "url": prop["url"],
        "source": prop["source"],
        "images": prop["images"],  # JSON array of image URLs
        "status": "scraped",
    }, headers=HEADERS, timeout=10)

    # Optionally download images to RustFS for permanent storage
    for img_url in prop["images"][:5]:  # Limit to 5 images
        img_data = httpx.get(img_url, timeout=30).content
        # Upload to RustFS via S3 API
        # Then update Directus item with RustFS URLs

@flow(name="Property Scraper")
async def scrape_properties(urls: list[str]):
    for url in urls:
        prop = await scrape_property(url)
        save_property(prop)
```

### Directus Collection Schema for Properties

```
properties:
  - title: string
  - description: text
  - price: float
  - currency: string
  - location: string
  - bedrooms: integer
  - bathrooms: integer
  - area_m2: float
  - images: json (array of URLs)
  - url: string (source listing URL)
  - source: string (website name)
  - status: string (scraped, verified, published)
  - latitude: float
  - longitude: float
```

### Viewing in UI
Directus Admin shows JSON fields as expandable objects.
For a custom property viewer, the frontend (CopilotKit) can:
1. Fetch properties from Directus REST API
2. Render image galleries from the `images` JSON array
3. Show on a map using latitude/longitude

## Crawl4AI: OSS Capabilities

Crawl4AI OSS (Apache 2.0) is fully capable for our use case:
- JavaScript rendering via Playwright
- Anti-bot detection (v0.8.5)
- Deep crawl with BFS/DFS strategies
- LLM-ready markdown output
- Image and media extraction
- Session management (login, cookies)
- Proxy support
- Docker deployment

Installed as a Python dependency in Prefect workers.
Not a separate service — it's a library that flows import.

### Limitations vs Cloud
- No managed proxy rotation (add your own)
- Lower anti-bot success rate (72% vs 90% with proxies)
- You manage Chromium/Playwright updates

### When to Consider Cloud
- Scraping sites with aggressive anti-bot (Cloudflare, DataDome)
- Need >1000 pages/hour sustained
- Don't want to manage browser infrastructure
