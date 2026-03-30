"""
QYNE v1 — Prefect API Tools.

Allows agents to trigger, list, and check Prefect flow runs.
The Automation Agent uses these to execute background tasks on demand.

IMPORTANT: trigger_prefect_flow validates parameters against known schemas
before sending to Prefect. This prevents the LLM from inventing parameter
names that cause SignatureMismatchError.
"""

import json
import os

import httpx
from agno.tools.decorator import tool

PREFECT_API_URL = os.getenv("PREFECT_API_URL", "http://prefect:4200/api")

# Known deployment parameter schemas — prevents LLM from inventing params
_DEPLOYMENT_SCHEMAS: dict[str, dict[str, str]] = {
    "643ba6b2-debb-42f1-938b-e7098bd2f42c": {  # website-crawler-ondemand
        "url": "str (required)",
        "max_pages": "int (default 50)",
        "max_depth": "int (default 3)",
        "include_paths": "list[str] or null",
        "exclude_paths": "list[str] or null",
        "index_in_knowledge": "bool (default true)",
        "max_chunk_tokens": "int (default 500)",
    },
    "c2848a70-7efb-4626-b8b2-776e3962e190": {  # etl-documents-on-demand
        "file_paths": "list[str]",
        "collection": "str",
    },
    "83ad0016-676d-4c36-baf9-36aba54d0bbd": {  # property-pipeline-6h
        "sites": "list[str]",
        "max_pages": "int",
        "download_images": "bool",
    },
    "9aa59a06-322c-4107-8cd5-80b5f6eeb406": {  # export-csv-ondemand
        "collection": "str",
        "fields": "str",
        "bucket": "str",
    },
}


def _prefect_request(method: str, path: str, json_data: dict | None = None) -> dict:
    """Make a request to the Prefect API."""
    try:
        resp = httpx.request(
            method,
            f"{PREFECT_API_URL}{path}",
            json=json_data,
            timeout=15,
        )
        if resp.is_success:
            return resp.json() if resp.content else {"status": "ok"}
        return {"error": f"Prefect {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"error": f"Prefect connection failed: {e}"}


def _validate_parameters(deployment_id: str, params: dict) -> str | None:
    """Validate parameters against known schema. Returns error message or None."""
    schema = _DEPLOYMENT_SCHEMAS.get(deployment_id)
    if not schema:
        return None  # Unknown deployment, skip validation

    # Check for invalid parameter names
    invalid = [k for k in params if k not in schema]
    if invalid:
        valid_names = ", ".join(schema.keys())
        return (
            f"Invalid parameter names: {invalid}. "
            f"Valid parameters for this deployment: {valid_names}. "
            f"Fix the parameter names and try again."
        )
    return None


@tool()
def list_prefect_deployments() -> str:
    """List all available Prefect deployments (background flows).

    Use this to see what flows are available before triggering one.
    Returns deployment names, IDs, schedules, and paused status.
    """
    result = _prefect_request("POST", "/deployments/filter", json_data={"limit": 20})
    if "error" in result:
        return f"Error: {result['error']}"

    if not result:
        return "No deployments found."

    lines = ["Available deployments:"]
    for d in result:
        name = d.get("name", "unknown")
        flow_name = d.get("flow_name", "?")
        paused = d.get("paused", False)
        schedule = d.get("schedule", {})
        cron = schedule.get("cron", "manual") if schedule else "manual"
        status = "PAUSED" if paused else "ACTIVE"
        lines.append(f"- **{flow_name}/{name}** [{status}] schedule={cron} id={d['id']}")

    return "\n".join(lines)


@tool()
def trigger_prefect_flow(deployment_id: str, parameters: str = "{}") -> str:
    """Trigger a Prefect flow run by deployment ID.

    Use list_prefect_deployments first to get the deployment ID.
    Parameters MUST match the flow's expected parameter names exactly.

    Args:
        deployment_id: The UUID of the deployment to trigger.
        parameters: JSON string of parameters. Use EXACT parameter names from the deployment schema.
    """
    try:
        params = json.loads(parameters)
    except json.JSONDecodeError:
        return f"Invalid JSON parameters: {parameters}"

    # Validate parameters against known schema
    error = _validate_parameters(deployment_id, params)
    if error:
        return f"Parameter validation failed: {error}"

    result = _prefect_request(
        "POST",
        f"/deployments/{deployment_id}/create_flow_run",
        json_data={"parameters": params},
    )

    if "error" in result:
        return f"Error triggering flow: {result['error']}"

    run_id = result.get("id", "unknown")
    flow_name = result.get("name", "unknown")
    return f"Flow triggered: {flow_name} (run_id={run_id}). Check Prefect dashboard for progress."


@tool()
def trigger_website_crawler(
    url: str,
    max_pages: int = 20,
    index_in_knowledge: bool = False,
) -> str:
    """Crawl a website and store pages in Directus.

    Call this when the user says "crawlea", "scrapea", or "extrae" a website.
    This is a shortcut that triggers the website-crawler Prefect flow.

    Args:
        url: The website URL to crawl (e.g. "https://example.com")
        max_pages: Maximum number of pages to crawl (default 20)
        index_in_knowledge: Whether to index in LanceDB for agent search (default false)
    """
    deployment_id = "643ba6b2-debb-42f1-938b-e7098bd2f42c"
    params = {
        "url": url,
        "max_pages": max_pages,
        "index_in_knowledge": index_in_knowledge,
    }

    result = _prefect_request(
        "POST",
        f"/deployments/{deployment_id}/create_flow_run",
        json_data={"parameters": params},
    )

    if "error" in result:
        return f"Error triggering crawler: {result['error']}"

    run_id = result.get("id", "unknown")
    flow_name = result.get("name", "unknown")
    return (
        f"Crawl activado: {flow_name} (run_id={run_id})\n"
        f"URL: {url}\n"
        f"Max paginas: {max_pages}\n"
        f"Indexar en knowledge: {'Si' if index_in_knowledge else 'No'}\n"
        f"El crawleo corre en background. Los datos se guardaran en Directus."
    )


@tool()
def check_prefect_flow_status(flow_run_id: str) -> str:
    """Check the status of a Prefect flow run.

    Args:
        flow_run_id: The UUID of the flow run to check.
    """
    result = _prefect_request("GET", f"/flow_runs/{flow_run_id}")

    if "error" in result:
        return f"Error: {result['error']}"

    name = result.get("name", "unknown")
    state = result.get("state", {})
    state_name = state.get("name", "unknown")
    duration = result.get("total_run_time", 0)

    return (
        f"Flow run: {name}\n"
        f"State: {state_name}\n"
        f"Duration: {duration}s"
    )


@tool()
def list_recent_flow_runs(limit: int = 5) -> str:
    """List recent Prefect flow runs with their status.

    Use this to check what flows ran recently and their results.
    """
    result = _prefect_request(
        "POST",
        "/flow_runs/filter",
        json_data={"limit": limit, "sort": "EXPECTED_START_TIME_DESC"},
    )

    if "error" in result:
        return f"Error: {result['error']}"

    if not result:
        return "No recent flow runs."

    lines = ["Recent flow runs:"]
    for run in result:
        name = run.get("name", "unknown")
        state = run.get("state", {}).get("name", "unknown")
        created = run.get("created", "")[:19]
        lines.append(f"- **{name}** [{state}] started={created}")

    return "\n".join(lines)
