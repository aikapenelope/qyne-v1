"""
QYNE v1 — Selector Health Check Flow.

Verifies that CSS selectors for each scraping site still work.
If a site returns 0 items, creates a critical alert in Directus.

Schedule: Weekly (Sunday 3am UTC) or on-demand.
"""

import json
import os
from datetime import datetime

import httpx
from prefect import flow, task
from prefect.logging import get_run_logger

DIRECTUS_URL = os.getenv("DIRECTUS_URL", "http://directus:8055")
DIRECTUS_TOKEN = os.getenv("DIRECTUS_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {DIRECTUS_TOKEN}", "Content-Type": "application/json"}


@task(retries=2, retry_delay_seconds=10)
async def check_site_selectors(site_name: str, site_config: dict) -> dict:
    """Fetch page 1 of a site and verify selectors extract data."""
    logger = get_run_logger()
    logger.info(f"Checking selectors for: {site_name}")

    result = {"site": site_name, "status": "ok", "items_found": 0, "error": None}

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
        from crawl4ai import JsonCssExtractionStrategy

        pagination = site_config["pagination"]
        if "{page}" in pagination:
            url = site_config["base_url"] + pagination.format(page=1)
        else:
            url = site_config["base_url"] + pagination.format(offset=0)

        config = CrawlerRunConfig(
            extraction_strategy=JsonCssExtractionStrategy(site_config["schema"]),
            cache_mode=CacheMode.BYPASS,
        )
        async with AsyncWebCrawler(headless=True, verbose=False) as crawler:
            crawl_result = await crawler.arun(url=url, config=config)

        if not crawl_result.success:
            result["status"] = "crawl_failed"
            result["error"] = "Page fetch failed"
            return result

        items = json.loads(crawl_result.extracted_content or "[]")
        result["items_found"] = len(items)

        if len(items) == 0:
            result["status"] = "selectors_broken"
            result["error"] = "CSS selectors returned 0 items — site HTML may have changed"
        elif len(items) < 3:
            result["status"] = "warning"
            result["error"] = f"Only {len(items)} items found — selectors may be partially broken"

        logger.info(f"  {site_name}: {len(items)} items → {result['status']}")
        return result

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)[:200]
        logger.error(f"  {site_name}: {e}")
        return result


@task
async def check_property_urls(sample_size: int = 20) -> dict:
    """Check a sample of property URLs for 404s (sold/removed)."""
    logger = get_run_logger()
    result = {"checked": 0, "alive": 0, "removed": 0, "errors": 0}

    if not DIRECTUS_TOKEN:
        return result

    try:
        resp = httpx.get(
            f"{DIRECTUS_URL}/items/properties?filter[status][_neq]=sold"
            f"&fields=id,url&sort=-date_created&limit={sample_size}",
            headers=HEADERS,
            timeout=10,
        )
        properties = resp.json().get("data", []) if resp.is_success else []

        for prop in properties:
            url = prop.get("url", "")
            if not url:
                continue
            result["checked"] += 1
            try:
                head = httpx.head(url, timeout=10, follow_redirects=True)
                if head.status_code == 404:
                    result["removed"] += 1
                    # Mark as sold
                    httpx.patch(
                        f"{DIRECTUS_URL}/items/properties/{prop['id']}",
                        json={
                            "status": "sold",
                            "sold_at": datetime.utcnow().isoformat(),
                        },
                        headers=HEADERS,
                        timeout=10,
                    )
                    logger.info(f"  Property {prop['id']} marked as sold (404)")
                else:
                    result["alive"] += 1
                    httpx.patch(
                        f"{DIRECTUS_URL}/items/properties/{prop['id']}",
                        json={"last_verified_at": datetime.utcnow().isoformat()},
                        headers=HEADERS,
                        timeout=10,
                    )
            except Exception:
                result["errors"] += 1

        logger.info(
            f"URL check: {result['checked']} checked, "
            f"{result['alive']} alive, {result['removed']} removed"
        )
    except Exception as e:
        logger.error(f"URL check failed: {e}")

    return result


@flow(name="Selector Health Check", log_prints=True)
async def selector_health_check(check_urls: bool = True, url_sample: int = 20) -> dict:
    """Verify scraping selectors and property URL freshness.

    Args:
        check_urls: Also check a sample of property URLs for 404s.
        url_sample: Number of URLs to check (default 20).
    """
    from flows.property_pipeline import SITE_CONFIGS

    results: dict = {"sites": {}, "urls": {}, "alerts": []}

    # Check each site's selectors
    for site_name, config in SITE_CONFIGS.items():
        site_result = await check_site_selectors(site_name, config)
        results["sites"][site_name] = site_result

        if site_result["status"] in ("selectors_broken", "crawl_failed", "error"):
            results["alerts"].append({
                "site": site_name,
                "status": site_result["status"],
                "error": site_result["error"],
            })

    # Check property URLs for 404s
    if check_urls:
        results["urls"] = await check_property_urls(url_sample)

    # Create alert in Directus if any issues
    if results["alerts"] and DIRECTUS_TOKEN:
        httpx.post(
            f"{DIRECTUS_URL}/items/events",
            json={
                "type": "selector_health_check",
                "payload": {
                    "alerts": results["alerts"],
                    "urls": results["urls"],
                    "timestamp": datetime.utcnow().isoformat(),
                },
            },
            headers=HEADERS,
            timeout=10,
        )

    # Log event even if no alerts
    if DIRECTUS_TOKEN:
        httpx.post(
            f"{DIRECTUS_URL}/items/events",
            json={
                "type": "selector_health_check",
                "payload": results,
            },
            headers=HEADERS,
            timeout=10,
        )

    return results
