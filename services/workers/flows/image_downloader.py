"""
QYNE v1 — Image Downloader Flow.

Downloads scraped image URLs to RustFS for permanent storage.
Updates Directus items with local RustFS URLs.

Schedule: On-demand (after scraping runs).
"""

import os
from pathlib import Path
from urllib.parse import urlparse
import hashlib

import httpx
from prefect import flow, task
from prefect.logging import get_run_logger

DIRECTUS_URL = os.getenv("DIRECTUS_URL", "http://directus:8055")
DIRECTUS_TOKEN = os.getenv("DIRECTUS_TOKEN", "")
RUSTFS_URL = os.getenv("RUSTFS_URL", "http://rustfs:9000")
RUSTFS_USER = os.getenv("RUSTFS_USER", "qyne")
RUSTFS_PASSWORD = os.getenv("RUSTFS_PASSWORD", "")
HEADERS = {"Authorization": f"Bearer {DIRECTUS_TOKEN}", "Content-Type": "application/json"}


@task(retries=2, retry_delay_seconds=10)
def fetch_items_with_images(collection: str = "scraped_data", limit: int = 50) -> list[dict]:
    """Fetch items that have image URLs but haven't been downloaded yet."""
    logger = get_run_logger()
    resp = httpx.get(
        f"{DIRECTUS_URL}/items/{collection}?limit={limit}&sort=-date_created"
        f"&fields=id,title,content",
        headers=HEADERS,
        timeout=15,
    )
    if not resp.is_success:
        return []
    items = resp.json().get("data", [])
    # Filter items with image URLs in content field
    with_images = []
    for item in items:
        content = item.get("content", "")
        if content and ("http" in content) and (".jpg" in content or ".png" in content or ".webp" in content):
            with_images.append(item)
    logger.info(f"Found {len(with_images)} items with images to download")
    return with_images


@task(retries=3, retry_delay_seconds=15)
def download_image(url: str, bucket: str = "images") -> str | None:
    """Download an image and upload to RustFS."""
    logger = get_run_logger()
    if not url or not RUSTFS_PASSWORD:
        return None

    try:
        # Download image
        resp = httpx.get(url, timeout=30, follow_redirects=True)
        if not resp.is_success:
            return None

        # Generate filename from URL hash
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        ext = Path(urlparse(url).path).suffix or ".jpg"
        filename = f"{url_hash}{ext}"

        # Ensure bucket exists
        httpx.put(
            f"{RUSTFS_URL}/{bucket}",
            auth=(RUSTFS_USER, RUSTFS_PASSWORD),
            timeout=10,
        )

        # Upload to RustFS
        upload_resp = httpx.put(
            f"{RUSTFS_URL}/{bucket}/{filename}",
            content=resp.content,
            auth=(RUSTFS_USER, RUSTFS_PASSWORD),
            timeout=30,
        )

        if upload_resp.is_success:
            local_url = f"{RUSTFS_URL}/{bucket}/{filename}"
            logger.info(f"Uploaded: {filename} ({len(resp.content)} bytes)")
            return local_url
        return None

    except Exception as e:
        logger.warning(f"Download failed for {url}: {e}")
        return None


@flow(name="Image Downloader", log_prints=True)
def image_downloader(
    collection: str = "scraped_data",
    bucket: str = "images",
    limit: int = 50,
) -> dict:
    """Download scraped image URLs to RustFS."""
    items = fetch_items_with_images(collection, limit)

    stats = {"items_processed": 0, "images_downloaded": 0, "errors": 0}
    for item in items:
        import json
        try:
            urls = json.loads(item.get("content", "[]"))
        except (json.JSONDecodeError, TypeError):
            continue

        if not isinstance(urls, list):
            continue

        local_urls = []
        for url in urls[:5]:  # Max 5 images per item
            local_url = download_image(url, bucket)
            if local_url:
                local_urls.append(local_url)
                stats["images_downloaded"] += 1
            else:
                stats["errors"] += 1

        stats["items_processed"] += 1

    return stats


if __name__ == "__main__":
    image_downloader()
