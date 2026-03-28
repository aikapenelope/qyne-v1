"""
QYNE v1 — Property Scraper Flow (Production 7-Stage Pipeline).

Fetch → Extract → Normalize → Validate → Dedup → Enrich → Store.
Uses Crawl4AI with CSS schemas per site. No LLM, no tokens.

Schedule: Every 6 hours (configurable).
"""

import json
import os
import re
from datetime import datetime

import httpx
from prefect import flow, task
from prefect.logging import get_run_logger

DIRECTUS_URL = os.getenv("DIRECTUS_URL", "http://directus:8055")
DIRECTUS_TOKEN = os.getenv("DIRECTUS_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {DIRECTUS_TOKEN}", "Content-Type": "application/json"}

# ---------------------------------------------------------------------------
# Site configurations (CSS schemas per site)
# ---------------------------------------------------------------------------

SITE_CONFIGS = {
    "mercadolibre_ve": {
        "base_url": "https://inmuebles.mercadolibre.com.ve/venta/",
        "pagination": "_Desde_{offset}_NoIndex_True",
        "items_per_page": 48,
        "max_pages": 5,
        "country": "VE",
        "currency_default": "USD",
        "wait_selector": "li.ui-search-layout__item",
        "delay_seconds": 2.0,
        "schema": {
            "name": "MercadoLibre VE Properties",
            "baseSelector": "li.ui-search-layout__item",
            "fields": [
                {"name": "title", "selector": "h2.ui-search-item__title", "type": "text"},
                {"name": "price_raw", "selector": "span.andes-money-amount__fraction", "type": "text"},
                {"name": "currency_symbol", "selector": "span.andes-money-amount__currency-symbol", "type": "text"},
                {"name": "location", "selector": "span.ui-search-item__location", "type": "text"},
                {"name": "url", "selector": "a.ui-search-link", "type": "attribute", "attribute": "href"},
                {"name": "image_url", "selector": "img", "type": "attribute", "attribute": "data-src"},
                {"name": "attrs", "selector": "li.ui-search-card-attributes__attribute", "type": "text"},
            ],
        },
    },
}

# ---------------------------------------------------------------------------
# Stage 1: FETCH
# ---------------------------------------------------------------------------


@task(retries=3, retry_delay_seconds=30)
async def fetch_page(url: str, site_config: dict) -> list[dict]:
    """Fetch and extract structured data from a page using Crawl4AI."""
    logger = get_run_logger()
    logger.info(f"Fetching: {url}")

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
        from crawl4ai import JsonCssExtractionStrategy

        strategy = JsonCssExtractionStrategy(site_config["schema"])
        config = CrawlerRunConfig(
            extraction_strategy=strategy,
            cache_mode=CacheMode.BYPASS,
        )

        async with AsyncWebCrawler(headless=True, verbose=False) as crawler:
            result = await crawler.arun(url=url, config=config)

        if not result.success:
            logger.warning(f"Crawl failed: {url}")
            return []

        items = json.loads(result.extracted_content or "[]")
        logger.info(f"Extracted {len(items)} items from {url}")
        return items

    except Exception as e:
        logger.error(f"Fetch error: {e}")
        return []


# ---------------------------------------------------------------------------
# Stage 3: NORMALIZE
# ---------------------------------------------------------------------------


def _parse_price(raw: str) -> float | None:
    if not raw:
        return None
    cleaned = re.sub(r"[^\d]", "", raw)
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def _extract_number(text: str, keyword: str) -> int | None:
    if not text:
        return None
    match = re.search(rf"(\d+)\s*{keyword}", text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _extract_area(text: str) -> float | None:
    if not text:
        return None
    match = re.search(r"(\d+[\.,]?\d*)\s*m", text)
    if match:
        return float(match.group(1).replace(",", "."))
    return None


CURRENCY_MAP = {"$": "USD", "Bs": "VES", "Bs.": "VES", "US$": "USD", "COP$": "COP"}


@task
def normalize_item(raw: dict, site_name: str) -> dict:
    """Stage 3: Clean and normalize extracted data."""
    config = SITE_CONFIGS[site_name]
    base_url = config["base_url"]

    url = raw.get("url", "")
    if url and not url.startswith("http"):
        url = f"{base_url.rstrip('/')}{url}"

    attrs = raw.get("attrs", "")

    return {
        "title": (raw.get("title") or "").strip()[:500],
        "price": _parse_price(raw.get("price_raw", "")),
        "currency": CURRENCY_MAP.get((raw.get("currency_symbol") or "").strip(), config["currency_default"]),
        "location": (raw.get("location") or "").strip(),
        "country": config["country"],
        "url": url,
        "image_urls": [raw["image_url"]] if raw.get("image_url") else [],
        "bedrooms": _extract_number(attrs, "habitaci|dormitorio|cuarto"),
        "bathrooms": _extract_number(attrs, "ba[ñn]o"),
        "area_m2": _extract_area(attrs),
        "source": site_name,
        "scraped_at": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Stage 4: VALIDATE
# ---------------------------------------------------------------------------


@task
def validate_item(item: dict) -> tuple[bool, list[str]]:
    """Stage 4: Check data quality."""
    errors = []
    if not item.get("title"):
        errors.append("missing title")
    if not item.get("url"):
        errors.append("missing url")
    if item.get("price") is not None and item["price"] <= 0:
        errors.append(f"invalid price: {item['price']}")
    if item.get("price") and item["price"] > 100_000_000:
        errors.append(f"price too high: {item['price']}")
    if item.get("area_m2") is not None and item["area_m2"] <= 0:
        errors.append(f"invalid area: {item['area_m2']}")
    return (len(errors) == 0, errors)


# ---------------------------------------------------------------------------
# Stage 5: DEDUPLICATE
# ---------------------------------------------------------------------------


@task(retries=1)
def check_duplicate(url: str) -> bool:
    """Stage 5: Check if URL already exists in Directus."""
    if not DIRECTUS_TOKEN or not url:
        return False
    resp = httpx.get(
        f"{DIRECTUS_URL}/items/properties?filter[url][_eq]={url}&fields=id&limit=1",
        headers=HEADERS,
        timeout=10,
    )
    if resp.is_success:
        return len(resp.json().get("data", [])) > 0
    return False


# ---------------------------------------------------------------------------
# Stage 6: ENRICH
# ---------------------------------------------------------------------------


@task
def enrich_item(item: dict) -> dict:
    """Stage 6: Add computed fields."""
    enriched = {**item}
    if item.get("price") and item.get("area_m2") and item["area_m2"] > 0:
        enriched["price_per_m2"] = round(item["price"] / item["area_m2"], 2)
    price = item.get("price") or 0
    if price < 50000:
        enriched["price_category"] = "budget"
    elif price < 200000:
        enriched["price_category"] = "mid"
    else:
        enriched["price_category"] = "premium"
    enriched["status"] = "scraped"
    return enriched


# ---------------------------------------------------------------------------
# Stage 7: STORE
# ---------------------------------------------------------------------------


@task(retries=2, retry_delay_seconds=10)
def store_item(item: dict) -> dict:
    """Stage 7: Write to Directus properties collection as PWA-ready JSON."""
    if not DIRECTUS_TOKEN:
        return {"status": "skipped"}

    # Build the property record — ready for direct UI consumption
    property_data = {
        "title": item.get("title", ""),
        "description": item.get("description", ""),
        "price": item.get("price"),
        "currency": item.get("currency", "USD"),
        "price_per_m2": item.get("price_per_m2"),
        "price_category": item.get("price_category", ""),
        "location": item.get("location", ""),
        "city": item.get("city", ""),
        "country": item.get("country", ""),
        "bedrooms": item.get("bedrooms"),
        "bathrooms": item.get("bathrooms"),
        "area_m2": item.get("area_m2"),
        "property_type": item.get("property_type", ""),
        # JSON fields — stored as native JSON in PostgreSQL
        # A PWA reads these directly from the API response
        "images": item.get("image_urls", []),
        "features": item.get("features", []),
        "url": item.get("url", ""),
        "source": item.get("source", ""),
        "status": item.get("status", "scraped"),
        "scraped_at": item.get("scraped_at"),
    }

    resp = httpx.post(
        f"{DIRECTUS_URL}/items/properties",
        json=property_data,
        headers=HEADERS,
        timeout=10,
    )
    if resp.is_success:
        return {"status": "saved", "id": resp.json()["data"]["id"]}
    return {"status": "error", "code": resp.status_code}


@task(retries=1)
def log_scrape_event(stats: dict) -> None:
    """Log scrape run stats to Directus events."""
    if not DIRECTUS_TOKEN:
        return
    httpx.post(
        f"{DIRECTUS_URL}/items/events",
        json={"type": "scrape_run", "payload": stats},
        headers=HEADERS,
        timeout=10,
    )


# ---------------------------------------------------------------------------
# Main Flow
# ---------------------------------------------------------------------------


@flow(name="Property Scraper", log_prints=True)
async def property_scraper(
    sites: list[str] | None = None,
    max_pages: int | None = None,
) -> dict:
    """Production 7-stage property scraping pipeline."""
    sites = sites or list(SITE_CONFIGS.keys())
    stats = {"fetched": 0, "valid": 0, "duplicates": 0, "saved": 0, "errors": 0}

    for site_name in sites:
        config = SITE_CONFIGS[site_name]
        pages = max_pages or config.get("max_pages", 5)

        for page in range(pages):
            offset = page * config.get("items_per_page", 48)
            url = config["base_url"] + config["pagination"].format(offset=offset)

            # Stage 1+2: Fetch + Extract
            items = await fetch_page(url, config)
            stats["fetched"] += len(items)

            for raw in items:
                # Stage 3: Normalize
                normalized = normalize_item(raw, site_name)

                # Stage 4: Validate
                is_valid, errors = validate_item(normalized)
                if not is_valid:
                    stats["errors"] += 1
                    continue
                stats["valid"] += 1

                # Stage 5: Deduplicate
                if check_duplicate(normalized.get("url", "")):
                    stats["duplicates"] += 1
                    continue

                # Stage 6: Enrich
                enriched = enrich_item(normalized)

                # Stage 7: Store
                result = store_item(enriched)
                if result.get("status") == "saved":
                    stats["saved"] += 1
                else:
                    stats["errors"] += 1

    log_scrape_event(stats)
    return stats


if __name__ == "__main__":
    import asyncio
    asyncio.run(property_scraper())
