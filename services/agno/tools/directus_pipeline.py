"""
QYNE v1 — Sales Pipeline Tools.

Tools for managing deals through the sales pipeline.
Deals represent potential revenue from a customer for a specific product.
Pipeline stages: lead -> qualified -> proposal -> negotiation -> won | lost

These tools are used by support agents when a conversation transitions
from support to sales (e.g., customer asks about pricing, wants to upgrade,
or is ready to buy).
"""

import httpx

from agno.tools.decorator import tool

from app.config import DIRECTUS_URL, DIRECTUS_TOKEN

_HEADERS = {
    "Authorization": f"Bearer {DIRECTUS_TOKEN}",
    "Content-Type": "application/json",
}

# Valid pipeline stages in order
PIPELINE_STAGES = ["lead", "qualified", "proposal", "negotiation", "won", "lost"]


def _directus_create(collection: str, data: dict) -> dict:
    """Create a record in Directus."""
    if not DIRECTUS_TOKEN:
        return {"error": "DIRECTUS_TOKEN not configured"}
    try:
        resp = httpx.post(
            f"{DIRECTUS_URL}/items/{collection}",
            json=data,
            headers=_HEADERS,
            timeout=10,
        )
        if resp.is_success:
            return resp.json()
        return {"error": f"Directus {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"error": f"Directus connection failed: {e}"}


def _directus_read(collection: str, filters: dict, fields: str = "*", limit: int = 10) -> list:
    """Read records from Directus with filters."""
    if not DIRECTUS_TOKEN:
        return []
    try:
        params: dict = {"limit": str(limit), "fields": fields, "sort": "-date_created"}
        for key, value in filters.items():
            params[f"filter[{key}][_eq]"] = str(value)
        resp = httpx.get(
            f"{DIRECTUS_URL}/items/{collection}",
            params=params,
            headers=_HEADERS,
            timeout=10,
        )
        if resp.is_success:
            return resp.json().get("data", [])
    except Exception:
        pass
    return []


def _directus_update(collection: str, item_id: int, data: dict) -> dict:
    """Update a record in Directus."""
    if not DIRECTUS_TOKEN:
        return {"error": "DIRECTUS_TOKEN not configured"}
    try:
        resp = httpx.patch(
            f"{DIRECTUS_URL}/items/{collection}/{item_id}",
            json=data,
            headers=_HEADERS,
            timeout=10,
        )
        if resp.is_success:
            return resp.json()
        if resp.status_code == 403:
            return {"warning": "UPDATE permission not granted"}
        return {"error": f"Directus {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"error": f"Directus connection failed: {e}"}


# ---------------------------------------------------------------------------
# Deal management
# ---------------------------------------------------------------------------

@tool()
def create_deal(
    product: str,
    contact_name: str,
    value: float,
    stage: str = "lead",
    probability: int = 10,
    notes: str = "",
    contact_id: int = 0,
    company_id: int = 0,
) -> str:
    """Create a new deal in the sales pipeline.

    Use this when a customer shows buying intent: asks about pricing,
    requests a demo, wants to upgrade, or mentions budget.

    Args:
        product: docflow, aurora, or nova
        contact_name: Customer name for reference
        value: Estimated deal value in USD (monthly)
        stage: Pipeline stage (lead, qualified, proposal, negotiation)
        probability: Likelihood of closing (0-100)
        notes: Context about the deal
        contact_id: Link to contact record (if known)
        company_id: Link to company record (if known)
    """
    if stage not in PIPELINE_STAGES:
        stage = "lead"

    deal_data: dict = {
        "product": product,
        "contact_name": contact_name,
        "value": value,
        "stage": stage,
        "probability": probability,
        "notes": notes,
        "status": "open",
    }
    if contact_id:
        deal_data["contact_id"] = contact_id
    if company_id:
        deal_data["company_id"] = company_id

    result = _directus_create("deals", deal_data)

    deal_id = result.get("data", {}).get("id") if "data" in result else None

    # Log the event
    _directus_create(
        "events",
        {
            "type": "deal_created",
            "payload": {
                "deal_id": deal_id,
                "product": product,
                "contact_name": contact_name,
                "value": value,
                "stage": stage,
            },
        },
    )

    if "error" in result:
        return f"DEAL_ERROR: {result['error']}"

    return (
        f"DEAL_CREATED: id={deal_id} product={product} "
        f"contact={contact_name} value=${value}/mes "
        f"stage={stage} probability={probability}%"
        f" — Registrado en pipeline"
    )


@tool()
def update_deal_stage(
    deal_id: int,
    new_stage: str,
    reason: str = "",
    probability: int = -1,
    lost_reason: str = "",
) -> str:
    """Move a deal to a new stage in the pipeline.

    Use this when a deal progresses (or is lost):
    - Customer qualifies (lead -> qualified)
    - Proposal sent (qualified -> proposal)
    - Negotiating terms (proposal -> negotiation)
    - Deal closed (negotiation -> won)
    - Deal lost at any stage (any -> lost)

    Args:
        deal_id: The deal ID to update
        new_stage: Target stage (qualified, proposal, negotiation, won, lost)
        reason: Why the stage changed
        probability: New probability (auto-set if not provided)
        lost_reason: Required if new_stage is 'lost'
    """
    if new_stage not in PIPELINE_STAGES:
        return f"INVALID_STAGE: {new_stage}. Valid: {', '.join(PIPELINE_STAGES)}"

    update_data: dict = {"stage": new_stage}

    # Auto-set probability based on stage if not explicitly provided
    if probability < 0:
        stage_probabilities = {
            "lead": 10,
            "qualified": 30,
            "proposal": 50,
            "negotiation": 75,
            "won": 100,
            "lost": 0,
        }
        probability = stage_probabilities.get(new_stage, 50)

    update_data["probability"] = probability

    if new_stage == "won":
        update_data["status"] = "won"
    elif new_stage == "lost":
        update_data["status"] = "lost"
        if lost_reason:
            update_data["lost_reason"] = lost_reason

    result = _directus_update("deals", deal_id, update_data)

    # Log the stage change
    _directus_create(
        "events",
        {
            "type": "deal_stage_changed",
            "payload": {
                "deal_id": deal_id,
                "new_stage": new_stage,
                "probability": probability,
                "reason": reason,
                "lost_reason": lost_reason,
            },
        },
    )

    if "error" in result:
        return f"DEAL_UPDATE_ERROR: {result['error']}"
    if "warning" in result:
        return f"DEAL_UPDATE_SKIPPED: {result['warning']} (need UPDATE permission on deals)"

    return (
        f"DEAL_UPDATED: id={deal_id} stage={new_stage} "
        f"probability={probability}%"
        f"{f' reason={reason}' if reason else ''}"
        f"{f' lost_reason={lost_reason}' if lost_reason else ''}"
    )


@tool()
def get_contact_deals(
    contact_name: str = "",
    product: str = "",
    stage: str = "",
    phone: str = "",
) -> str:
    """Look up deals in the pipeline.

    Use this to check if a customer already has an open deal,
    or to review the pipeline for a product.

    Args:
        contact_name: Filter by customer name
        product: Filter by product (docflow, aurora, nova)
        stage: Filter by stage
        phone: Look up deals by customer phone (finds contact first)
    """
    filters: dict = {}
    if contact_name:
        filters["contact_name"] = contact_name
    if product:
        filters["product"] = product
    if stage:
        filters["stage"] = stage

    # If phone provided, try to find contact_id
    if phone and not contact_name:
        from tools.directus_business import _find_contact_by_phone
        contact = _find_contact_by_phone(phone)
        if contact:
            filters["contact_id"] = contact["id"]

    deals = _directus_read("deals", filters, limit=10)

    if not deals:
        return "NO_DEALS_FOUND: No matching deals in the pipeline."

    lines = [f"DEALS_FOUND: {len(deals)} deal(s)"]
    for d in deals:
        lines.append(
            f"  - id={d.get('id')} {d.get('product','')} "
            f"contact={d.get('contact_name','')} "
            f"${d.get('value',0)}/mes stage={d.get('stage','')} "
            f"prob={d.get('probability',0)}% "
            f"status={d.get('status','')}"
        )
    return "\n".join(lines)


@tool()
def get_pipeline_summary(product: str = "") -> str:
    """Get a summary of the sales pipeline.

    Use this when asked about pipeline status, forecasting, or revenue projections.
    Returns count and total value per stage.

    Args:
        product: Filter by product (optional, shows all if empty)
    """
    filters: dict = {}
    if product:
        filters["product"] = product

    deals = _directus_read(
        "deals",
        filters,
        fields="id,product,value,stage,probability,status",
        limit=100,
    )

    if not deals:
        return "PIPELINE_EMPTY: No deals in the pipeline."

    # Aggregate by stage
    stages: dict = {}
    for d in deals:
        s = d.get("stage", "unknown")
        if s not in stages:
            stages[s] = {"count": 0, "value": 0.0, "weighted": 0.0}
        stages[s]["count"] += 1
        val = float(d.get("value", 0) or 0)
        prob = float(d.get("probability", 0) or 0)
        stages[s]["value"] += val
        stages[s]["weighted"] += val * (prob / 100)

    total_value = sum(s["value"] for s in stages.values())
    total_weighted = sum(s["weighted"] for s in stages.values())
    total_deals = sum(s["count"] for s in stages.values())

    lines = [
        f"PIPELINE_SUMMARY: {total_deals} deals, "
        f"${total_value:.0f}/mes total, "
        f"${total_weighted:.0f}/mes weighted"
        f"{f' (product: {product})' if product else ''}",
        "",
    ]
    for stage_name in PIPELINE_STAGES:
        if stage_name in stages:
            s = stages[stage_name]
            lines.append(
                f"  {stage_name:15s}: {s['count']} deals, "
                f"${s['value']:.0f}/mes, "
                f"${s['weighted']:.0f}/mes weighted"
            )

    return "\n".join(lines)
