"""
QYNE v1 — Dedup Merger Flow.

Finds duplicate contacts by email and merges them intelligently.
Keeps the most complete record, merges fields from duplicates.

Schedule: Weekly or on-demand.
"""

import os

import httpx
from prefect import flow, task
from prefect.logging import get_run_logger

DIRECTUS_URL = os.getenv("DIRECTUS_URL", "http://directus:8055")
DIRECTUS_TOKEN = os.getenv("DIRECTUS_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {DIRECTUS_TOKEN}", "Content-Type": "application/json"}


@task(retries=2, retry_delay_seconds=10)
def find_duplicates() -> list[dict]:
    """Find contacts with duplicate emails."""
    logger = get_run_logger()
    resp = httpx.get(
        f"{DIRECTUS_URL}/items/contacts?fields=id,first_name,last_name,email,phone,company,product,lead_score,source,date_created&limit=1000&sort=email",
        headers=HEADERS,
        timeout=15,
    )
    if not resp.is_success:
        return []

    contacts = resp.json().get("data", [])
    seen: dict[str, list[dict]] = {}
    for c in contacts:
        email = (c.get("email") or "").lower().strip()
        if email:
            seen.setdefault(email, []).append(c)

    duplicates = [{"email": email, "records": records}
                  for email, records in seen.items() if len(records) > 1]

    logger.info(f"Found {len(duplicates)} duplicate email groups")
    return duplicates


@task
def merge_records(records: list[dict]) -> tuple[dict, list[int]]:
    """Merge duplicate records. Keep most complete, merge missing fields."""
    # Sort by completeness (most non-null fields first)
    def completeness(r: dict) -> int:
        return sum(1 for v in r.values() if v is not None and v != "")

    sorted_records = sorted(records, key=completeness, reverse=True)
    primary = {**sorted_records[0]}
    ids_to_remove = []

    for dup in sorted_records[1:]:
        # Merge missing fields from duplicates into primary
        for key, value in dup.items():
            if key == "id":
                continue
            if (primary.get(key) is None or primary.get(key) == "") and value:
                primary[key] = value
        # Keep highest lead score
        if (dup.get("lead_score") or 0) > (primary.get("lead_score") or 0):
            primary["lead_score"] = dup["lead_score"]
        ids_to_remove.append(dup["id"])

    return primary, ids_to_remove


@task
def generate_merge_report(duplicates: list[dict], dry_run: bool) -> str:
    """Generate a report of what would be merged."""
    lines = [
        f"# Dedup Report ({'DRY RUN' if dry_run else 'EXECUTED'})",
        f"Found {len(duplicates)} duplicate groups",
        "",
    ]
    for group in duplicates[:20]:
        email = group["email"]
        count = len(group["records"])
        ids = [r["id"] for r in group["records"]]
        lines.append(f"- **{email}**: {count} records (IDs: {ids})")

    return "\n".join(lines)


@task(retries=1)
def save_report(report: str) -> None:
    """Save merge report to Directus events."""
    httpx.post(
        f"{DIRECTUS_URL}/items/events",
        json={"type": "dedup_report", "payload": {"report": report}},
        headers=HEADERS,
        timeout=10,
    )


@flow(name="Dedup Merger", log_prints=True)
def dedup_merger(dry_run: bool = True) -> dict:
    """Find and optionally merge duplicate contacts.

    Args:
        dry_run: If True, only report duplicates. If False, merge them.
    """
    duplicates = find_duplicates()

    stats = {"groups": len(duplicates), "merged": 0, "dry_run": dry_run}

    for group in duplicates:
        primary, ids_to_remove = merge_records(group["records"])

        if not dry_run:
            # Update primary record with merged data
            httpx.patch(
                f"{DIRECTUS_URL}/items/contacts/{primary['id']}",
                json={k: v for k, v in primary.items() if k != "id"},
                headers=HEADERS,
                timeout=10,
            )
            stats["merged"] += 1

    report = generate_merge_report(duplicates, dry_run)
    save_report(report)

    return stats


if __name__ == "__main__":
    dedup_merger(dry_run=True)
