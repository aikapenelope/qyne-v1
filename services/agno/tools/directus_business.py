"""
NEXUS Cerebro — Directus Business Logic Tools.

These tools implement business-specific operations that go beyond simple CRUD.
Generic CRUD is handled by the Directus MCP server (auto-discovered).
These tools add: approval workflows, escalation, CRM-specific logic.
"""

import httpx

from agno.approval.decorator import approval
from agno.tools.decorator import tool

from app.config import DIRECTUS_URL, DIRECTUS_TOKEN

_HEADERS = {
    "Authorization": f"Bearer {DIRECTUS_TOKEN}",
    "Content-Type": "application/json",
}


def _directus_create(collection: str, data: dict) -> dict:
    """Create a record in Directus via REST API. Returns the response or error."""
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


@approval  # type: ignore[arg-type]
@tool(requires_confirmation=True)
def confirm_payment(
    product: str,
    client_name: str,
    amount: str,
    method: str,
    reference: str = "",
) -> str:
    """Confirm a client payment. Requires human approval before processing.

    Use this when a client says they made a payment or wants to pay.
    The payment will be held until an admin approves it.
    After approval, the payment is logged in Directus CRM.
    """
    result = _directus_create(
        "payments",
        {
            "amount": float(amount) if amount.replace(".", "").isdigit() else 0,
            "method": method,
            "reference": reference,
            "status": "approved",
            "approved_by": "nexus-agent",
            "product": product,
        },
    )

    _directus_create(
        "tasks",
        {
            "title": f"Seguimiento pago: {client_name} ({product})",
            "body": f"Pago de {amount} via {method}. Ref: {reference}. Verificar acreditacion.",
            "status": "TODO",
        },
    )

    if "error" in result:
        return f"PAYMENT_APPROVED (CRM error: {result['error']}): {client_name} {amount} {method}"

    return (
        f"PAYMENT_CONFIRMED_AND_LOGGED: product={product} client={client_name} "
        f"amount={amount} method={method} ref={reference} — Registrado en Directus"
    )


@approval(type="audit")
@tool(requires_confirmation=True)
def log_support_ticket(
    product: str,
    intent: str,
    summary: str,
    resolution: str,
    urgency: str = "medium",
    lead_score: int = 0,
) -> str:
    """Log a support interaction to the CRM for tracking and analytics.

    Call this after resolving any customer query to maintain records.
    """
    result = _directus_create(
        "tickets",
        {
            "product": product,
            "intent": intent,
            "summary": summary,
            "resolution": resolution,
            "urgency": urgency,
            "status": "resolved" if resolution else "open",
        },
    )

    if urgency == "high" or lead_score >= 7:
        _directus_create(
            "tasks",
            {
                "title": f"Follow-up: {product} - {intent} (score: {lead_score})",
                "body": f"Urgencia: {urgency}. {summary[:200]}",
                "status": "todo",
            },
        )

    if "error" in result:
        return f"TICKET_LOGGED (CRM error: {result['error']}): {product} {intent}"

    return (
        f"TICKET_LOGGED: product={product} intent={intent} urgency={urgency} "
        f"lead_score={lead_score} — Registrado en Directus"
    )


@tool()
def escalate_to_human(
    product: str,
    reason: str,
    client_name: str = "unknown",
    urgency: str = "high",
) -> str:
    """Escalate a conversation to a human agent.

    Use when: complaint is serious, payment dispute, legal/compliance issue,
    client explicitly asks for a human, or you cannot resolve the issue.
    """
    result = _directus_create(
        "tasks",
        {
            "title": f"ESCALACION: {product} - {client_name}",
            "body": (
                f"Producto: {product}\n"
                f"Cliente: {client_name}\n"
                f"Urgencia: {urgency}\n"
                f"Razon: {reason}\n"
                f"Estado: REQUIERE ATENCION HUMANA"
            ),
            "status": "todo",
        },
    )

    if "error" in result:
        return f"ESCALATED (CRM error: {result['error']}): {product} {client_name} {reason}"

    return (
        f"ESCALATED_AND_LOGGED: product={product} client={client_name} urgency={urgency} "
        f"reason={reason} — Tarea creada en Directus para atencion humana"
    )


@tool()
def save_contact(
    first_name: str,
    last_name: str = "",
    email: str = "",
    phone: str = "",
    job_title: str = "",
    city: str = "",
    company_name: str = "",
    lead_score: int = 0,
    product: str = "",
    notes: str = "",
) -> str:
    """Save or update a contact in Directus CRM.

    ALWAYS call this when you learn a client's name, email, phone, or company.
    """
    person_data: dict = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
    }
    if job_title:
        person_data["job_title"] = job_title
    if city:
        person_data["city"] = city
    if product:
        person_data["product"] = product
    if lead_score > 0:
        person_data["lead_score"] = lead_score
    if company_name:
        person_data["notes"] = f"Empresa: {company_name}"
    person_data["source"] = "whatsapp"
    person_data["status"] = "lead"

    result = _directus_create("contacts", person_data)

    if "error" in result:
        return f"CONTACT_SAVED (CRM error: {result['error']}): {first_name} {last_name}"

    return (
        f"CONTACT_SAVED: {first_name} {last_name}"
        f"{f' ({email})' if email else ''}"
        f"{f' tel:{phone}' if phone else ''}"
        f"{f' empresa:{company_name}' if company_name else ''}"
        f" — Registrado en Directus"
    )


@tool()
def save_company(
    name: str,
    domain: str = "",
    employees: int = 0,
    industry: str = "",
    address: str = "",
    notes: str = "",
) -> str:
    """Save a company in Directus CRM.

    Call this when a client mentions their company name.
    """
    company_data: dict = {"name": name}
    if domain:
        company_data["domainName"] = domain
    if employees > 0:
        company_data["employees"] = employees
    if address:
        company_data["address"] = address

    result = _directus_create("companies", company_data)

    if "error" in result:
        return f"COMPANY_SAVED (CRM error: {result['error']}): {name}"

    return f"COMPANY_SAVED: {name}{f' ({domain})' if domain else ''} — Registrado en Directus"
