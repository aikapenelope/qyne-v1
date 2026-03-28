"""
QYNE v1 — Image Downloader Flow.

Downloads property images from external URLs to RustFS.
Organizes by property ID: rustfs:9000/properties/{property_id}/{hash}.jpg
Updates Directus images[] JSON with permanent RustFS URLs.

Schedule: On-demand (after property scraper runs).
"""

import hashlib
import os
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

BUCKET = "properties"
MAX_IMAGES_PER_PROPERTY = 10


@task(retries=2, retry_delay_seconds=10)
def fetch_properties_with_external_images(limit: int = 50) -> list[dict]:
    """Fetch properties that have external image URLs (not yet downloaded)."""
    logger = get_run_logger()
    resp = httpx.get(
        f"{DIRECTUS_URL}/items/properties"
        f"?limit={limit}&sort=-date_created&fields=id,title,images,status"
        f"&filter[status][_eq]=scraped",
        headers=HEADERS,
        timeout=15,
    )
    if not resp.is_success:
        return []

    items = resp.json().get("data", [])
    # Filter: only items with images that have source=original (not yet downloaded)
    with_external = []
    for item in items:
        images = item.get("images") or []
        if isinstance(images, list) and any(
            isinstance(img, dict) and img.get("source") == "original"
            for img in images
        ):
            with_external.append(item)

    logger.info(f"Found {len(with_external)} properties with external images")
    return with_external


@task(retries=3, retry_delay_seconds=15)
def download_and_upload_image(
    image_url: str,
    property_id: int,
    order: int,
) -> dict | None:
    """Download an image and upload to RustFS organized by property ID."""
    logger = get_run_logger()
    if not image_url or not RUSTFS_PASSWORD:
        return None

    try:
        # Download from external URL
        resp = httpx.get(image_url, timeout=30, follow_redirects=True)
        if not resp.is_success or len(resp.content) < 1000:
            return None

        # Generate filename: {property_id}/{hash}.{ext}
        url_hash = hashlib.md5(image_url.encode()).hexdigest()[:12]
        ext = Path(urlparse(image_url).path).suffix or ".jpg"
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            ext = ".jpg"
        path = f"{property_id}/{url_hash}{ext}"

        # Ensure bucket exists
        httpx.put(
            f"{RUSTFS_URL}/{BUCKET}",
            auth=(RUSTFS_USER, RUSTFS_PASSWORD),
            timeout=10,
        )

        # Upload to RustFS: properties/{property_id}/{hash}.jpg
        upload_resp = httpx.put(
            f"{RUSTFS_URL}/{BUCKET}/{path}",
            content=resp.content,
            auth=(RUSTFS_USER, RUSTFS_PASSWORD),
            timeout=30,
        )

        if upload_resp.is_success:
            size_kb = len(resp.content) / 1024
            logger.info(f"Uploaded: {BUCKET}/{path} ({size_kb:.0f} KB)")
            return {
                "url": f"{RUSTFS_URL}/{BUCKET}/{path}",
                "original_url": image_url,
                "order": order,
                "source": "rustfs",
                "size_bytes": len(resp.content),
                "filename": f"{url_hash}{ext}",
            }
        return None

    except Exception as e:
        logger.warning(f"Failed: {image_url} → {e}")
        return None


@task(retries=2, retry_delay_seconds=5)
def update_property_images(property_id: int, images: list[dict]) -> bool:
    """Update property images in Directus with RustFS URLs."""
    resp = httpx.patch(
        f"{DIRECTUS_URL}/items/properties/{property_id}",
        json={
            "images": images,
            "status": "images_downloaded",
        },
        headers=HEADERS,
        timeout=10,
    )
    return resp.is_success


@task(retries=1)
def log_download_event(stats: dict) -> None:
    """Log download stats to Directus events."""
    if DIRECTUS_TOKEN:
        httpx.post(
            f"{DIRECTUS_URL}/items/events",
            json={"type": "image_download", "payload": stats},
            headers=HEADERS,
            timeout=10,
        )


@flow(name="Image Downloader", log_prints=True)
def image_downloader(limit: int = 50) -> dict:
    """Download external images to RustFS, organized by property ID.

    Structure: rustfs:9000/properties/{property_id}/{hash}.jpg
    Updates Directus images[] JSON with permanent URLs + metadata.
    """
    properties = fetch_properties_with_external_images(limit)

    stats = {"properties": 0, "downloaded": 0, "failed": 0, "skipped": 0}

    for prop in properties:
        property_id = prop["id"]
        images = prop.get("images") or []
        if not isinstance(images, list):
            continue

        updated_images = []
        for img in images[:MAX_IMAGES_PER_PROPERTY]:
            if not isinstance(img, dict):
                continue

            if img.get("source") == "rustfs":
                # Already downloaded, keep as-is
                updated_images.append(img)
                stats["skipped"] += 1
                continue

            # Download and upload to RustFS
            result = download_and_upload_image(
                image_url=img.get("url", ""),
                property_id=property_id,
                order=img.get("order", 0),
            )

            if result:
                result["alt"] = img.get("alt", "")
                updated_images.append(result)
                stats["downloaded"] += 1
            else:
                # Keep original URL as fallback
                updated_images.append(img)
                stats["failed"] += 1

        # Update property with new image URLs
        if updated_images:
            update_property_images(property_id, updated_images)
            stats["properties"] += 1

    log_download_event(stats)
    return stats


if __name__ == "__main__":
    image_downloader()
