"""
NEXUS Cerebro — LATAM Scraper Flow (Prefect).

Deterministic web scraping pipeline. NO AI involved.
Fetches data from configured sources, parses HTML, and stores in Directus.

Schedule: Every 6 hours (configurable via Prefect UI).
"""

import os

import httpx
from prefect import flow, task
from prefect.logging import get_run_logger

DIRECTUS_URL = os.getenv("DIRECTUS_URL", "http://directus:8055")
DIRECTUS_TOKEN = os.getenv("DIRECTUS_TOKEN", "")


@task(retries=3, retry_delay_seconds=30)
def fetch_page(url: str) -> str:
    """Fetch a web page and return its HTML content."""
    logger = get_run_logger()
    logger.info(f"Fetching: {url}")
    resp = httpx.get(url, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


@task
def parse_content(html: str, source: str) -> list[dict]:
    """Parse HTML and extract structured data. Deterministic, no AI."""
    from bs4 import BeautifulSoup

    logger = get_run_logger()
    soup = BeautifulSoup(html, "html.parser")

    # Example: extract article titles and links
    items = []
    for article in soup.select("article, .listing, .property-card")[:20]:
        title_el = article.select_one("h2, h3, .title")
        link_el = article.select_one("a[href]")
        if title_el:
            items.append(
                {
                    "title": title_el.get_text(strip=True),
                    "url": link_el["href"] if link_el else "",
                    "source": source,
                }
            )

    logger.info(f"Parsed {len(items)} items from {source}")
    return items


@task(retries=2, retry_delay_seconds=10)
def save_to_directus(items: list[dict], collection: str = "scraped_data") -> int:
    """Save parsed items to Directus via REST API. Deterministic."""
    if not DIRECTUS_TOKEN or not items:
        return 0

    logger = get_run_logger()
    headers = {
        "Authorization": f"Bearer {DIRECTUS_TOKEN}",
        "Content-Type": "application/json",
    }

    saved = 0
    for item in items:
        resp = httpx.post(
            f"{DIRECTUS_URL}/items/{collection}",
            json=item,
            headers=headers,
            timeout=10,
        )
        if resp.is_success:
            saved += 1

    logger.info(f"Saved {saved}/{len(items)} items to Directus/{collection}")
    return saved


@flow(name="LATAM Scraper", log_prints=True)
def scraper_latam(
    urls: list[str] | None = None,
    collection: str = "scraped_data",
) -> dict:
    """Main scraping flow. Fetches, parses, and stores data deterministically.

    Args:
        urls: List of URLs to scrape. Defaults to configured sources.
        collection: Directus collection to store results.
    """
    if urls is None:
        urls = [
            # Add your LATAM data sources here
            # "https://example.com/listings",
        ]

    total_saved = 0
    for url in urls:
        html = fetch_page(url)
        items = parse_content(html, source=url)
        saved = save_to_directus(items, collection=collection)
        total_saved += saved

    return {"urls_processed": len(urls), "items_saved": total_saved}


if __name__ == "__main__":
    scraper_latam()
