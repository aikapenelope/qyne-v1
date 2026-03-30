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
        "scrape_details": False,
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
    "rentahouse_ve": {
        "base_url": "https://rentahouse.com.ve/buscar-propiedades",
        "pagination": "?page={page}&orderBy=entryTimestamp%20desc",
        "items_per_page": 20,
        "max_pages": 5,
        "country": "VE",
        "currency_default": "USD",
        "delay_seconds": 3.0,
        "scrape_details": True,
        "schema": {
            "name": "RentAHouse VE Properties",
            "baseSelector": "div.card",
            "fields": [
                {"name": "title", "selector": "img", "type": "attribute", "attribute": "alt"},
                {"name": "price_raw", "selector": "div.price strong", "type": "text"},
                {"name": "url", "selector": "a", "type": "attribute", "attribute": "href"},
                {"name": "image_url", "selector": "img", "type": "attribute", "attribute": "src"},
                {"name": "dormitorios", "selector": "td.dormitorio", "type": "text"},
                {"name": "banos", "selector": "td.baño", "type": "text"},
                {"name": "estacionamiento", "selector": "td.puesto", "type": "text"},
                {"name": "superficie", "selector": "td.superficie", "type": "text"},
                {"name": "location", "selector": "div.card-footer span", "type": "text"},
                {"name": "rah_code", "selector": "span.property-code", "type": "text"},
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


@task(retries=2, retry_delay_seconds=10)
async def fetch_detail_page(url: str) -> dict:
    """Fetch a property detail page and extract full info including realtor.

    Extracts: description, all images (high quality), operation type,
    structured fields, features, construction details, location, realtor + WhatsApp.
    """
    logger = get_run_logger()
    logger.info(f"Fetching detail: {url}")
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, BrowserConfig

        bc = BrowserConfig(headless=True, java_script_enabled=True)
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            page_timeout=20000,
            delay_before_return_html=3.0,
        )
        async with AsyncWebCrawler(config=bc) as crawler:
            result = await crawler.arun(url=url, config=config)

        if not result.success:
            logger.warning(f"Detail crawl failed: {url}")
            return {}

        md = result.markdown or ""
        html = result.html or ""
        detail: dict = {"source_url": url}

        # --- Operation type (venta/alquiler) from URL or title ---
        url_lower = url.lower()
        if "alquiler" in url_lower or "alquiler" in md[:200].lower():
            detail["operation"] = "alquiler"
        elif "venta" in url_lower or "venta" in md[:200].lower():
            detail["operation"] = "venta"

        # --- All images (high quality 1280x1024) ---
        all_images = []
        img_urls = re.findall(
            r"https://cdn\.(?:photos|resize)\.sparkplatform\.com/ven/(?:1280x1024/true/)?(\S+?)(?:-[ot])?\.jpg",
            html,
        )
        # Deduplicate by base ID and build high-quality URLs
        seen_ids: set[str] = set()
        for raw_id in img_urls:
            base_id = re.sub(r"-[ot]$", "", raw_id).split("/")[-1]
            if base_id not in seen_ids:
                seen_ids.add(base_id)
                hq_url = f"https://cdn.resize.sparkplatform.com/ven/1280x1024/true/{base_id}-o.jpg"
                all_images.append({
                    "url": hq_url,
                    "order": len(all_images),
                    "source": "rentahouse_cdn",
                })
        if all_images:
            detail["all_images"] = all_images
            logger.info(f"Found {len(all_images)} images")

        # --- Description ---
        desc_start = md.find("## Descripción\n")
        desc_end = md.find("## Descripción General")
        if desc_start >= 0 and desc_end > desc_start:
            detail["description"] = md[desc_start + 15:desc_end].strip()

        # --- Structured fields from "Descripción General" ---
        gen_start = md.find("## Descripción General")
        gen_end = md.find("## Detalles")
        if gen_start >= 0:
            section = md[gen_start:gen_end] if gen_end > gen_start else md[gen_start:gen_start + 2000]
            for line in section.split("\n"):
                line = line.strip().lstrip("* ").lstrip("- ")
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip().lower().replace(" ", "_")
                    val = val.strip()
                    if key and val and not key.startswith("!["):
                        detail[f"field_{key}"] = val

        # --- Features from Detalles + Dispositivos + Construccion ---
        features = []
        secondary_details: dict[str, str] = {}

        for section_name in ["## Detalles", "## Dispositivos", "## Construcción"]:
            sec_start = md.find(section_name)
            if sec_start < 0:
                continue
            # Find end (next ## or end of text)
            sec_end = md.find("\n## ", sec_start + len(section_name))
            section = md[sec_start:sec_end] if sec_end > sec_start else md[sec_start:sec_start + 1000]

            for line in section.split("\n"):
                line_clean = line.strip().lstrip("* ").lstrip("- ")
                if "✅" in line_clean:
                    feat = line_clean.replace("✅", "").strip()
                    if feat:
                        features.append(feat)
                elif ":" in line_clean and not line_clean.startswith("#"):
                    key, val = line_clean.split(":", 1)
                    key = key.strip()
                    val = val.strip()
                    if key and val:
                        secondary_details[key] = val

        detail["features"] = features
        if secondary_details:
            detail["construction_details"] = secondary_details

        # --- Location ---
        loc_start = md.find("## Ubicación")
        if loc_start >= 0:
            loc_section = md[loc_start:loc_start + 500]
            for line in loc_section.split("\n"):
                line = line.strip().lstrip("* ").lstrip("- ")
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip().lower()
                    val = val.strip()
                    if key in ("país", "estado", "ciudad", "urbanización", "pais", "urbanizacion"):
                        detail[f"loc_{key}"] = val

        # --- Realtor name and WhatsApp ---
        contact_start = md.find("### Contactar")
        if contact_start >= 0:
            contact_section = md[contact_start:contact_start + 500]
            for line in contact_section.split("\n"):
                if line.startswith("## ") and "Contactar" not in line:
                    detail["realtor_name"] = line.replace("## ", "").strip()
                wa_match = re.search(r"wa\.me/(\d+)", line)
                if wa_match:
                    detail["realtor_whatsapp"] = wa_match.group(1)

        # --- RAH code ---
        rah_match = re.search(r"rah-(\d{2}-\d{4,6})", html, re.I)
        if rah_match:
            detail["rah_code"] = f"VE {rah_match.group(1)}"

        logger.info(
            f"Detail extracted: {len(detail)} fields, "
            f"images={len(all_images)}, features={len(features)}, "
            f"realtor={detail.get('realtor_name', 'N/A')}"
        )
        return detail

    except Exception as e:
        logger.error(f"Detail fetch error: {e}")
        return {}


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
    url = raw.get("source_url") or raw.get("url", "")
    if url and not url.startswith("http"):
        url = f"{config['base_url'].rstrip('/')}{url}"

    attrs = raw.get("attrs", "")
    title = (raw.get("title") or "").strip()
    location = (raw.get("location") or "").strip()
    description = raw.get("description") or title

    # Extract features (from attrs text or from detail page features list)
    features = raw.get("features", [])
    if not features and attrs:
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

    # Extract city — from detail page location fields or from listing
    city = raw.get("loc_ciudad", "")
    state = raw.get("loc_estado", "")
    neighborhood = raw.get("loc_urbanización") or raw.get("loc_urbanizacion", "")
    if not city:
        city = location.split(",")[0].strip() if location else ""
    if state or neighborhood:
        location = ", ".join(filter(None, [neighborhood, city, state]))

    # Build image objects — prefer all_images from detail page
    image_urls = []
    if raw.get("all_images"):
        image_urls = raw["all_images"]
    elif raw.get("image_url"):
        image_urls.append({
            "url": raw["image_url"],
            "alt": title[:80],
            "order": 0,
            "source": "original",
        })

    # Price: from detail page fields or from listing
    price_raw = raw.get("price_raw", "")
    if not price_raw:
        price_raw = raw.get("field_**usd", "") or raw.get("field_usd", "")

    # Bedrooms/bathrooms: from detail fields or from listing attrs
    bedrooms = None
    bathrooms = None
    area = None
    parking = None

    # Try detail page fields first
    for key, val in raw.items():
        if key.startswith("field_"):
            val_str = str(val).strip()
            if "dormitorio" in key:
                bedrooms = _extract_number(val_str, "") or int(re.sub(r"\D", "", val_str) or "0") or None
            elif "baño" in key or "bano" in key:
                bathrooms = _extract_number(val_str, "") or int(re.sub(r"\D", "", val_str) or "0") or None
            elif "área" in key or "area" in key:
                area = _extract_area(val_str)

    # Fall back to listing page fields
    if not bedrooms:
        bedrooms = int(raw["dormitorios"]) if raw.get("dormitorios") and raw["dormitorios"].strip().isdigit() else _extract_number(attrs, "habitaci|dormitorio|cuarto")
    if not bathrooms:
        bathrooms = int(raw["banos"]) if raw.get("banos") and raw["banos"].strip().isdigit() else _extract_number(attrs, "ba[ñn]o")
    if not area:
        superficie = raw.get("superficie", "")
        area = _extract_area(superficie) if superficie else _extract_area(attrs)
    if raw.get("estacionamiento") and raw["estacionamiento"].strip().isdigit():
        parking = int(raw["estacionamiento"])

    result = {
        "title": title[:500],
        "description": description[:5000],
        "price": _parse_price(price_raw),
        "currency": CURRENCY_MAP.get((raw.get("currency_symbol") or "").strip(), config["currency_default"]),
        "location": location,
        "city": city,
        "state": state,
        "neighborhood": neighborhood,
        "country": config["country"],
        "url": url,
        "images": image_urls,
        "features": features,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "parking": parking,
        "area_m2": area,
        "property_type": prop_type,
        "source": site_name,
        "scraped_at": datetime.utcnow().isoformat(),
    }

    # Add rentahouse-specific fields
    if raw.get("rah_code"):
        result["external_id"] = raw["rah_code"]
    if raw.get("realtor_name"):
        result["realtor_name"] = raw["realtor_name"]
    if raw.get("realtor_whatsapp"):
        result["realtor_phone"] = raw["realtor_whatsapp"]
    if raw.get("operation"):
        result["operation"] = raw["operation"]
    if raw.get("construction_details"):
        result["construction_details"] = raw["construction_details"]

    return result


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
            # Build URL: some sites use offset, others use page number
            pagination = config["pagination"]
            if "{page}" in pagination:
                url = config["base_url"] + pagination.format(page=page + 1)
            else:
                url = config["base_url"] + pagination.format(offset=offset)

            # Stage 1+2: Fetch + Extract
            raw_items = await fetch_and_extract(url, config)
            stats["fetched"] += len(raw_items)

            for raw in raw_items:
                # Stage 2.5: Fetch detail page if configured
                if config.get("scrape_details") and raw.get("url"):
                    detail_url = raw["url"]
                    if not detail_url.startswith("http"):
                        detail_url = "https://rentahouse.com.ve" + detail_url
                    detail = await fetch_detail_page(detail_url)
                    if detail:
                        raw.update(detail)

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
