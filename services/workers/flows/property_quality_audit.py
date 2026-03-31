"""
QYNE v1 — Property Data Quality Audit Flow.

Checks all properties in Directus for missing required fields,
incomplete data, and stale records. Creates a report in Directus events.

Schedule: Weekly (Sunday 4am UTC) or on-demand.
"""

import os
from datetime import datetime, timedelta

import httpx
from prefect import flow, task
from prefect.logging import get_run_logger

DIRECTUS_URL = os.getenv("DIRECTUS_URL", "http://directus:8055")
DIRECTUS_TOKEN = os.getenv("DIRECTUS_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {DIRECTUS_TOKEN}", "Content-Type": "application/json"}

REQUIRED_FIELDS = ["title", "price", "city", "url", "source", "images"]
RECOMMENDED_FIELDS = ["bedrooms", "bathrooms", "area_m2", "realtor_name", "realtor_phone", "operation", "external_id"]


@task
def count_properties() -> int:
    """Get total property count."""
    try:
        resp = httpx.get(
            f"{DIRECTUS_URL}/items/properties",
            params={"aggregate[count]": "id"},
            headers=HEADERS,
            timeout=10,
        )
        data = resp.json().get("data", [])
        return int(data[0]["count"]["id"]) if data else 0
    except Exception:
        return 0


@task
def check_missing_fields(field: str) -> int:
    """Count properties missing a specific field."""
    try:
        resp = httpx.get(
            f"{DIRECTUS_URL}/items/properties",
            params={f"filter[{field}][_null]": "true", "aggregate[count]": "id"},
            headers=HEADERS,
            timeout=10,
        )
        data = resp.json().get("data", [])
        return int(data[0]["count"]["id"]) if data else 0
    except Exception:
        return -1


@task
def check_empty_images() -> int:
    """Count properties with empty images array."""
    try:
        resp = httpx.get(
            f"{DIRECTUS_URL}/items/properties",
            params={"filter[images][_empty]": "true", "aggregate[count]": "id"},
            headers=HEADERS,
            timeout=10,
        )
        data = resp.json().get("data", [])
        return int(data[0]["count"]["id"]) if data else 0
    except Exception:
        return -1


@task
def check_stale_properties(days: int = 30) -> int:
    """Count properties not verified in N days."""
    try:
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        resp = httpx.get(
            f"{DIRECTUS_URL}/items/properties",
            params={
                "filter[last_verified_at][_lt]": cutoff,
                "filter[status][_neq]": "sold",
                "aggregate[count]": "id",
            },
            headers=HEADERS,
            timeout=10,
        )
        data = resp.json().get("data", [])
        return int(data[0]["count"]["id"]) if data else 0
    except Exception:
        return -1


@task
def count_by_source() -> dict:
    """Count properties per source."""
    try:
        resp = httpx.get(
            f"{DIRECTUS_URL}/items/properties",
            params={"groupBy[]": "source", "aggregate[count]": "id"},
            headers=HEADERS,
            timeout=10,
        )
        data = resp.json().get("data", [])
        return {item["source"]: int(item["count"]["id"]) for item in data if item.get("source")}
    except Exception:
        return {}


@task
def count_by_status() -> dict:
    """Count properties per status."""
    try:
        resp = httpx.get(
            f"{DIRECTUS_URL}/items/properties",
            params={"groupBy[]": "status", "aggregate[count]": "id"},
            headers=HEADERS,
            timeout=10,
        )
        data = resp.json().get("data", [])
        return {item["status"]: int(item["count"]["id"]) for item in data if item.get("status")}
    except Exception:
        return {}


@flow(name="Property Quality Audit", log_prints=True)
async def property_quality_audit(stale_days: int = 30) -> dict:
    """Audit property data quality and create report."""
    logger = get_run_logger()
    report: dict = {
        "timestamp": datetime.utcnow().isoformat(),
        "total": 0,
        "by_source": {},
        "by_status": {},
        "missing_required": {},
        "missing_recommended": {},
        "empty_images": 0,
        "stale": 0,
        "issues": [],
    }

    report["total"] = count_properties()
    report["by_source"] = count_by_source()
    report["by_status"] = count_by_status()

    # Check required fields
    for field in REQUIRED_FIELDS:
        missing = check_missing_fields(field)
        if missing > 0:
            report["missing_required"][field] = missing
            report["issues"].append(f"{missing} properties missing required field '{field}'")
            logger.warning(f"QUALITY: {missing} properties missing '{field}'")

    # Check recommended fields
    for field in RECOMMENDED_FIELDS:
        missing = check_missing_fields(field)
        if missing > 0:
            report["missing_recommended"][field] = missing

    # Check empty images
    report["empty_images"] = check_empty_images()
    if report["empty_images"] > 0:
        report["issues"].append(f"{report['empty_images']} properties with no images")

    # Check stale
    report["stale"] = check_stale_properties(stale_days)
    if report["stale"] > 0:
        report["issues"].append(f"{report['stale']} properties not verified in {stale_days} days")

    # Completeness score
    total = report["total"]
    if total > 0:
        required_complete = total - sum(report["missing_required"].values())
        report["completeness_required"] = round(required_complete / total * 100, 1)
        recommended_complete = total - sum(report["missing_recommended"].values())
        report["completeness_recommended"] = round(recommended_complete / total * 100, 1)

    # Save report to Directus
    if DIRECTUS_TOKEN:
        httpx.post(
            f"{DIRECTUS_URL}/items/events",
            json={"type": "quality_audit", "payload": report},
            headers=HEADERS,
            timeout=10,
        )

    logger.info(f"Audit complete: {total} properties, {len(report['issues'])} issues")
    return report
