"""
QYNE v1 — Property Pipeline Flow (Complete).

Single flow that runs the entire property pipeline:
Scrape → Normalize → Validate → Dedup → Enrich → Store → Download Images.

Trigger from chat: "Scrapea propiedades de MercadoLibre Venezuela"
Trigger from Prefect: property_pipeline(sites=["mercadolibre_ve"])

Output: PWA-ready JSON in Directus properties collection with images in RustFS.
"""

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
from prefect import flow, task
from prefect.logging import get_run_logger

DIRECTUS_URL = os.getenv("DIRECTUS_URL", "http://directus:8055")
DIRECTUS_TOKEN = os.getenv("DIRECTUS_TOKEN", "")
RUSTFS_URL = os.getenv("RUSTFS_URL", "http://rustfs:9000")
RUSTFS_USER = os.getenv("RUSTFS_USER", "qyne")
RUSTFS_PASSWORD = os.getenv("RUSTFS_PASSWORD", "")
HEADERS = {"Authorization": f"Bearer {DIRECTUS_TOKEN}", "Content-Type": "application/json"}

# ---------------------------------------------------------------------------
# Site Configurations
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

CURRENCY_MAP = {"$": "USD", "Bs": "VES", "Bs.": "VES", "US$": "USD", "COP$": "COP"}

FEATURE_KEYWORDS = {
    "piscina": "piscina", "pool": "piscina",
    "estacionamiento": "estacionamiento", "parking": "estacionamiento",
    "jardin": "jardin", "garden": "jardin",
    "seguridad": "seguridad", "vigilancia": "seguridad",
    "ascensor": "ascensor", "gimnasio": "gimnasio",
    "terraza": "terraza", "balcon": "balcon",
    "amoblado": "amoblado", "furnished": "amoblado",
}

PROPERTY_TYPES = {
    "apartamento": "apartment", "apto": "apartment",
    "casa": "house", "townhouse": "house",
    "terreno": "land", "lote": "land", "parcela": "land",
    "oficina": "office", "local": "commercial",
    "penthouse": "penthouse", "ph": "penthouse",
    "finca": "farm", "hacienda": "farm",
}


# ---------------------------------------------------------------------------
# Stage 1: FETCH + EXTRACT
# ---------------------------------------------------------------------------


@task(retries=3, retry_delay_seconds=30)
async def fetch_and_extract(url: str, site_config: dict) -> list[dict]:
    """Fetch page and extract structured data with CSS schema."""
    logger = get_run_logger()
    logger.info(f"Fetching: {url}")
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
        from crawl4ai import JsonCssExtractionStrategy

        config = CrawlerRunConfig(
            extraction_strategy=JsonCssExtractionStrategy(site_config["schema"]),
            cache_mode=CacheMode.BYPASS,
        )
        async with AsyncWebCrawler(headless=True, verbose=False) as crawler:
            result = await crawler.arun(url=url, config=config)

        if not result.success:
            logger.warning(f"Crawl failed: {url}")
            return []

        items = json.loads(result.extracted_content or "[]")
        logger.info(f"Extracted {len(items)} items")
        return items
    except Exception as e:
        logger.error(f"Fetch error: {e}")
        return []


# ---------------------------------------------------------------------------
# Stage 2: NORMALIZE
# ---------------------------------------------------------------------------


def _parse_price(raw: str) -> float | None:
    if not raw:
        return None
    cleaned = re.sub(r"[^\d]", "", raw)
    return float(cleaned) if cleaned else None


def _extract_number(text: str, pattern: str) -> int | None:
    if not text:
        return None
    match = re.search(rf"(\d+)\s*(?:{pattern})", text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _extract_area(text: str) -> float | None:
    if not text:
        return None
    match = re.search(r"(\d+[\.,]?\d*)\s*m", text)
    return float(match.group(1).replace(",", ".")) if match else None


@task
def normalize(raw: dict, site_name: str) -> dict:
    """Clean and structure raw extracted data."""
    config = SITE_CONFIGS[site_name]
    url = raw.get("url", "")
    if url and not url.startswith("http"):
        url = f"{config['base_url'].rstrip('/')}{url}"

    attrs = raw.get("attrs", "")
    title = (raw.get("title") or "").strip()
    location = (raw.get("location") or "").strip()

    # Extract features
    features = []
    if attrs:
        text_lower = attrs.lower()
        for kw, feat in FEATURE_KEYWORDS.items():
            if kw in text_lower and feat not in features:
                features.append(feat)

    # Detect property type
    title_lower = title.lower()
    prop_type = "other"
    for kw, pt in PROPERTY_TYPES.items():
        if kw in title_lower:
            prop_type = pt
            break

    # Extract city
    city = location.split(",")[0].strip() if location else ""

    # Build image objects
    image_urls = []
    if raw.get("image_url"):
        image_urls.append({
            "url": raw["image_url"],
            "alt": title[:80],
            "order": 0,
            "source": "original",
        })

    return {
        "title": title[:500],
        "description": title,
        "price": _parse_price(raw.get("price_raw", "")),
        "currency": CURRENCY_MAP.get((raw.get("currency_symbol") or "").strip(), config["currency_default"]),
        "location": location,
        "city": city,
        "country": config["country"],
        "url": url,
        "images": image_urls,
        "features": features,
        "bedrooms": _extract_number(attrs, "habitaci|dormitorio|cuarto"),
        "bathrooms": _extract_number(attrs, "ba[ñn]o"),
        "area_m2": _extract_area(attrs),
        "property_type": prop_type,
        "source": site_name,
        "scraped_at": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Stage 3: VALIDATE
# ---------------------------------------------------------------------------


@task
def validate(item: dict) -> bool:
    """Reject bad data."""
    if not item.get("title") or not item.get("url"):
        return False
    if item.get("price") is not None and item["price"] <= 0:
        return False
    if item.get("price") and item["price"] > 100_000_000:
        return False
    return True


# ---------------------------------------------------------------------------
# Stage 4: DEDUP
# ---------------------------------------------------------------------------


@task(retries=1)
def is_duplicate(url: str) -> bool:
    """Check if URL already exists in properties."""
    if not DIRECTUS_TOKEN or not url:
        return False
    resp = httpx.get(
        f"{DIRECTUS_URL}/items/properties?filter[url][_eq]={url}&fields=id&limit=1",
        headers=HEADERS,
        timeout=10,
    )
    return len(resp.json().get("data", [])) > 0 if resp.is_success else False


# ---------------------------------------------------------------------------
# Stage 5: ENRICH
# ---------------------------------------------------------------------------


@task
def enrich(item: dict) -> dict:
    """Add computed fields."""
    enriched = {**item}
    if item.get("price") and item.get("area_m2") and item["area_m2"] > 0:
        enriched["price_per_m2"] = round(item["price"] / item["area_m2"], 2)
    price = item.get("price") or 0
    enriched["price_category"] = "budget" if price < 50000 else "mid" if price < 200000 else "premium"
    enriched["status"] = "scraped"
    return enriched


# ---------------------------------------------------------------------------
# Stage 6: STORE
# ---------------------------------------------------------------------------


@task(retries=2, retry_delay_seconds=10)
def store(item: dict) -> int | None:
    """Write to Directus properties. Returns property ID."""
    if not DIRECTUS_TOKEN:
        return None
    resp = httpx.post(
        f"{DIRECTUS_URL}/items/properties",
        json=item,
        headers=HEADERS,
        timeout=10,
    )
    if resp.is_success:
        return resp.json()["data"]["id"]
    return None


# ---------------------------------------------------------------------------
# Stage 7: DOWNLOAD IMAGES
# ---------------------------------------------------------------------------


@task(retries=3, retry_delay_seconds=15)
def download_image(image_url: str, property_id: int, order: int) -> dict | None:
    """Download image to RustFS: properties/{property_id}/{hash}.ext"""
    if not image_url or not RUSTFS_PASSWORD:
        return None
    try:
        resp = httpx.get(image_url, timeout=30, follow_redirects=True)
        if not resp.is_success or len(resp.content) < 1000:
            return None

        url_hash = hashlib.md5(image_url.encode()).hexdigest()[:12]
        ext = Path(urlparse(image_url).path).suffix or ".jpg"
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            ext = ".jpg"
        path = f"{property_id}/{url_hash}{ext}"

        httpx.put(f"{RUSTFS_URL}/properties", auth=(RUSTFS_USER, RUSTFS_PASSWORD), timeout=10)
        upload = httpx.put(
            f"{RUSTFS_URL}/properties/{path}",
            content=resp.content,
            auth=(RUSTFS_USER, RUSTFS_PASSWORD),
            timeout=30,
        )
        if upload.is_success:
            return {
                "url": f"{RUSTFS_URL}/properties/{path}",
                "original_url": image_url,
                "order": order,
                "source": "rustfs",
                "size_bytes": len(resp.content),
            }
    except Exception:
        pass
    return None


@task(retries=2, retry_delay_seconds=5)
def update_images(property_id: int, images: list[dict]) -> None:
    """Update property with downloaded image URLs."""
    httpx.patch(
        f"{DIRECTUS_URL}/items/properties/{property_id}",
        json={"images": images, "status": "ready"},
        headers=HEADERS,
        timeout=10,
    )


# ---------------------------------------------------------------------------
# MAIN FLOW
# ---------------------------------------------------------------------------


@flow(name="Property Pipeline", log_prints=True)
async def property_pipeline(
    sites: list[str] | None = None,
    max_pages: int | None = None,
    download_images: bool = True,
) -> dict:
    """Complete property pipeline: scrape → process → store → download images.

    One command does everything. Output is PWA-ready JSON in Directus.

    Args:
        sites: Site names from SITE_CONFIGS. Default: all sites.
        max_pages: Override max pages per site.
        download_images: Whether to download images to RustFS.
    """
    sites = sites or list(SITE_CONFIGS.keys())
    stats = {
        "fetched": 0, "valid": 0, "duplicates": 0,
        "saved": 0, "images_downloaded": 0, "errors": 0,
    }

    for site_name in sites:
        if site_name not in SITE_CONFIGS:
            continue
        config = SITE_CONFIGS[site_name]
        pages = max_pages or config.get("max_pages", 5)

        for page in range(pages):
            offset = page * config.get("items_per_page", 48)
            url = config["base_url"] + config["pagination"].format(offset=offset)

            # Stage 1+2: Fetch + Extract
            raw_items = await fetch_and_extract(url, config)
            stats["fetched"] += len(raw_items)

            for raw in raw_items:
                # Stage 3: Normalize
                item = normalize(raw, site_name)

                # Stage 4: Validate
                if not validate(item):
                    stats["errors"] += 1
                    continue
                stats["valid"] += 1

                # Stage 5: Dedup
                if is_duplicate(item.get("url", "")):
                    stats["duplicates"] += 1
                    continue

                # Stage 6: Enrich
                item = enrich(item)

                # Stage 7: Store
                property_id = store(item)
                if not property_id:
                    stats["errors"] += 1
                    continue
                stats["saved"] += 1

                # Stage 8: Download images (optional)
                if download_images and item.get("images"):
                    downloaded = []
                    for img in item["images"]:
                        if not isinstance(img, dict):
                            continue
                        result = download_image(
                            img.get("url", ""), property_id, img.get("order", 0)
                        )
                        if result:
                            result["alt"] = img.get("alt", "")
                            downloaded.append(result)
                            stats["images_downloaded"] += 1

                    if downloaded:
                        update_images(property_id, downloaded)

    # Log run summary
    if DIRECTUS_TOKEN:
        httpx.post(
            f"{DIRECTUS_URL}/items/events",
            json={"type": "property_pipeline", "payload": stats},
            headers=HEADERS,
            timeout=10,
        )

    return stats


if __name__ == "__main__":
    import asyncio
    asyncio.run(property_pipeline())
