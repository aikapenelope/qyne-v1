"""
QYNE v1 — Health Check Flow.

Verifies all services are responding. Logs results to Directus events.
Alerts via Directus task if any service is down.

Schedule: Every 5 minutes.
"""

import os
from datetime import datetime

import httpx
from prefect import flow, task
from prefect.logging import get_run_logger

DIRECTUS_URL = os.getenv("DIRECTUS_URL", "http://directus:8055")
DIRECTUS_TOKEN = os.getenv("DIRECTUS_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {DIRECTUS_TOKEN}", "Content-Type": "application/json"}

SERVICES = [
    {"name": "Agno", "url": "http://agno:8000/health"},
    {"name": "Directus", "url": "http://directus:8055/server/health"},
    {"name": "Frontend", "url": "http://frontend:3000"},
    {"name": "n8n", "url": "http://n8n:5678/healthz"},
    {"name": "Prefect", "url": "http://prefect:4200/api/health"},
    {"name": "Redis", "url": "http://redis:6379", "tcp": True},
    {"name": "RustFS", "url": "http://rustfs:9000/health"},
]


@task
def check_service(service: dict) -> dict:
    """Check if a service is responding."""
    logger = get_run_logger()
    name = service["name"]
    url = service["url"]

    try:
        if service.get("tcp"):
            import socket
            host, port = url.replace("http://", "").split(":")
            sock = socket.create_connection((host, int(port)), timeout=5)
            sock.close()
            status = "healthy"
            latency_ms = 0
        else:
            start = datetime.utcnow()
            resp = httpx.get(url, timeout=5)
            latency_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
            status = "healthy" if resp.status_code < 500 else "unhealthy"
    except Exception as e:
        status = "down"
        latency_ms = -1
        logger.warning(f"{name}: DOWN ({e})")

    return {"name": name, "status": status, "latency_ms": latency_ms}


@task(retries=1)
def log_results(results: list[dict]) -> None:
    """Log health check results to Directus events."""
    httpx.post(
        f"{DIRECTUS_URL}/items/events",
        json={"type": "health_check", "payload": {"services": results}},
        headers=HEADERS,
        timeout=10,
    )


@task
def alert_if_down(results: list[dict]) -> list[str]:
    """Create alert tasks for any down services."""
    logger = get_run_logger()
    down = [r for r in results if r["status"] == "down"]

    for service in down:
        logger.error(f"ALERT: {service['name']} is DOWN")
        httpx.post(
            f"{DIRECTUS_URL}/items/tasks",
            json={
                "title": f"ALERT: {service['name']} is DOWN",
                "body": f"Service {service['name']} failed health check at {datetime.utcnow().isoformat()}",
                "status": "todo",
                "assigned_to": "ops",
            },
            headers=HEADERS,
            timeout=10,
        )

    return [s["name"] for s in down]


@flow(name="Health Check", log_prints=True)
def health_check() -> dict:
    """Check all services and alert if any are down."""
    results = [check_service(s) for s in SERVICES]
    log_results(results)
    down_services = alert_if_down(results)

    healthy = sum(1 for r in results if r["status"] == "healthy")
    return {
        "total": len(results),
        "healthy": healthy,
        "down": down_services,
    }


if __name__ == "__main__":
    health_check()
