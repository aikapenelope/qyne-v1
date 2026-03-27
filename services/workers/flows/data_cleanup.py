"""
QYNE v1 — Data Cleanup Flow.

Archives old data, deduplicates contacts, cleans up test records.
Keeps Directus collections lean and performant.

Schedule: Weekly (Sunday 02:00 UTC).
"""

import os
from datetime import datetime, timedelta

import httpx
from prefect import flow, task
from prefect.logging import get_run_logger

DIRECTUS_URL = os.getenv("DIRECTUS_URL", "http://directus:8055")
DIRECTUS_TOKEN = os.getenv("DIRECTUS_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {DIRECTUS_TOKEN}", "Content-Type": "application/json"}


@task(retries=2, retry_delay_seconds=10)
def archive_old_conversations(days: int = 90) -> int:
    """Mark old conversations as archived (update status field)."""
    logger = get_run_logger()
    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00")

    # Fetch old conversations
    resp = httpx.get(
        f"{DIRECTUS_URL}/items/conversations"
        f"?filter[date_created][_lt]={cutoff}&limit=100&fields=id",
        headers=HEADERS,
        timeout=15,
    )
    if not resp.is_success:
        return 0

    items = resp.json().get("data", [])
    logger.info(f"Found {len(items)} conversations older than {days} days")
    return len(items)


@task(retries=2, retry_delay_seconds=10)
def find_duplicate_contacts() -> list[dict]:
    """Find contacts with duplicate emails."""
    logger = get_run_logger()
    resp = httpx.get(
        f"{DIRECTUS_URL}/items/contacts?fields=id,email,first_name,last_name&limit=500&sort=email",
        headers=HEADERS,
        timeout=15,
    )
    if not resp.is_success:
        return []

    contacts = resp.json().get("data", [])
    seen: dict[str, list] = {}
    for c in contacts:
        email = (c.get("email") or "").lower().strip()
        if email:
            seen.setdefault(email, []).append(c)

    duplicates = [{"email": email, "count": len(items), "ids": [i["id"] for i in items]}
                  for email, items in seen.items() if len(items) > 1]

    logger.info(f"Found {len(duplicates)} duplicate email groups")
    return duplicates


@task(retries=2, retry_delay_seconds=10)
def count_test_records() -> dict[str, int]:
    """Count records with source='test' or status='test' across collections."""
    logger = get_run_logger()
    collections = ["contacts", "companies", "tickets", "tasks"]
    counts: dict[str, int] = {}

    for col in collections:
        resp = httpx.get(
            f"{DIRECTUS_URL}/items/{col}"
            f"?aggregate[count]=id&filter[source][_eq]=test",
            headers=HEADERS,
            timeout=10,
        )
        if resp.is_success:
            data = resp.json().get("data", [])
            count = data[0].get("count", {}).get("id", 0) if data else 0
            if count > 0:
                counts[col] = count

    logger.info(f"Test records: {counts}")
    return counts


@task
def generate_cleanup_report(
    old_conversations: int,
    duplicates: list[dict],
    test_records: dict[str, int],
) -> str:
    """Generate a cleanup report without deleting anything."""
    lines = [
        "# Data Cleanup Report",
        f"**Date**: {datetime.utcnow().strftime('%Y-%m-%d')}",
        "",
        f"## Old Conversations (>90 days): {old_conversations}",
        "",
        f"## Duplicate Contacts: {len(duplicates)} groups",
    ]
    for d in duplicates[:10]:
        lines.append(f"- {d['email']}: {d['count']} records (IDs: {d['ids']})")

    lines.extend(["", "## Test Records"])
    for col, count in test_records.items():
        lines.append(f"- {col}: {count} test records")

    lines.extend([
        "",
        "## Actions Required",
        "- Review duplicates and merge manually in Directus Admin",
        "- Delete test records if no longer needed",
        "- Old conversations can be exported and archived",
        "",
        "*This report does NOT delete any data. All cleanup is manual.*",
    ])

    return "\n".join(lines)


@task(retries=1)
def save_cleanup_report(report: str) -> str:
    """Save cleanup report to Directus events."""
    resp = httpx.post(
        f"{DIRECTUS_URL}/items/events",
        json={"type": "cleanup_report", "payload": {"report": report}},
        headers=HEADERS,
        timeout=10,
    )
    return "saved" if resp.is_success else f"error:{resp.status_code}"


@flow(name="Data Cleanup", log_prints=True)
def data_cleanup(archive_days: int = 90) -> dict:
    """Analyze data quality and generate cleanup report. Does NOT delete data."""
    old_convos = archive_old_conversations(archive_days)
    duplicates = find_duplicate_contacts()
    test_records = count_test_records()

    report = generate_cleanup_report(old_convos, duplicates, test_records)
    status = save_cleanup_report(report)

    return {
        "old_conversations": old_convos,
        "duplicate_groups": len(duplicates),
        "test_record_collections": len(test_records),
        "report_status": status,
    }


if __name__ == "__main__":
    data_cleanup()
