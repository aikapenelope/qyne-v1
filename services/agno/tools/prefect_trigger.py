"""
NEXUS Cerebro — Prefect Trigger Tool.

Allows AI agents to trigger Prefect flows on demand.
"""

import os

import httpx

from agno.tools.decorator import tool

PREFECT_API_URL = os.getenv("PREFECT_API_URL", "http://prefect:4200/api")


@tool()
def trigger_prefect_flow(
    deployment_name: str,
    parameters: dict | None = None,
) -> str:
    """Trigger a Prefect flow deployment to run a background task.

    Available deployments:
    - "scraper-latam": Scrape LATAM data sources and save to Directus
    - "document-etl": Process documents with Docling and index in knowledge base

    Args:
        deployment_name: Name of the Prefect deployment to trigger.
        parameters: Optional parameters to pass to the flow.
    """
    try:
        resp = httpx.post(
            f"{PREFECT_API_URL}/deployments/filter",
            json={"deployments": {"name": {"any_": [deployment_name]}}},
            timeout=10,
        )
        if not resp.is_success:
            return f"ERROR: Could not find deployment '{deployment_name}': {resp.status_code}"

        deployments = resp.json()
        if not deployments:
            return f"ERROR: Deployment '{deployment_name}' not found"

        deployment_id = deployments[0]["id"]

        run_resp = httpx.post(
            f"{PREFECT_API_URL}/deployments/{deployment_id}/create_flow_run",
            json={"parameters": parameters or {}},
            timeout=10,
        )
        if run_resp.is_success:
            run_data = run_resp.json()
            return f"FLOW_TRIGGERED: {deployment_name} (run_id={run_data.get('id', 'unknown')})"
        return f"ERROR: Failed to trigger flow: {run_resp.status_code}"

    except Exception as e:
        return f"ERROR: Prefect connection failed: {e}"
