"""
QYNE v1 — Prefect API Tools.

Allows agents to trigger, list, and check Prefect flow runs.
The Automation Agent uses these to execute background tasks on demand.
"""

import os

import httpx
from agno.tools.decorator import tool

PREFECT_API_URL = os.getenv("PREFECT_API_URL", "http://prefect:4200/api")


def _prefect_request(method: str, path: str, json: dict | None = None) -> dict:
    """Make a request to the Prefect API."""
    try:
        resp = httpx.request(
            method,
            f"{PREFECT_API_URL}{path}",
            json=json,
            timeout=15,
        )
        if resp.is_success:
            return resp.json() if resp.content else {"status": "ok"}
        return {"error": f"Prefect {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"error": f"Prefect connection failed: {e}"}


@tool()
def list_prefect_deployments() -> str:
    """List all available Prefect deployments (background flows).

    Use this to see what flows are available before triggering one.
    Returns deployment names, IDs, schedules, and paused status.
    """
    result = _prefect_request("POST", "/deployments/filter", json={"limit": 20})
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
    Parameters should be a JSON string matching the flow's expected inputs.

    Args:
        deployment_id: The UUID of the deployment to trigger.
        parameters: JSON string of parameters (e.g. '{"urls": ["https://..."]}').
    """
    import json

    try:
        params = json.loads(parameters)
    except json.JSONDecodeError:
        return f"Invalid JSON parameters: {parameters}"

    result = _prefect_request(
        "POST",
        f"/deployments/{deployment_id}/create_flow_run",
        json={"parameters": params},
    )

    if "error" in result:
        return f"Error triggering flow: {result['error']}"

    run_id = result.get("id", "unknown")
    flow_name = result.get("name", "unknown")
    return f"Flow triggered: {flow_name} (run_id={run_id}). Check Prefect dashboard for progress."


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
    state_type = state.get("type", "unknown")
    state_name = state.get("name", "unknown")
    duration = result.get("total_run_time", 0)

    return (
        f"Flow run: {name}\n"
        f"State: {state_name} ({state_type})\n"
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
        json={"limit": limit, "sort": "EXPECTED_START_TIME_DESC"},
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
