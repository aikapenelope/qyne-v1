"""
QYNE v1 — Directus Business Logic Tools.

These tools implement business-specific operations that go beyond simple CRUD.
Generic CRUD is handled by the Directus MCP server (auto-discovered).
These tools add: approval workflows, escalation, CRM-specific logic,
contact upsert, and FK-linked records for a unified customer timeline.
"""

from typing import Optional

import httpx

from agno.approval.decorator import approval
from agno.tools.decorator import tool

from app.config import DIRECTUS_URL, DIRECTUS_TOKEN

_HEADERS = {
    "Authorization": f"Bearer {DIRECTUS_TOKEN}",
    "Content-Type": "application/json",
}


# ---------------------------------------------------------------------------
# Directus helpers
# ---------------------------------------------------------------------------

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


def _directus_read(
    collection: str,
    filters: dict,
    fields: str = "*",
    limit: int = 1,
) -> list:
    """Read records from Directus with filters. Returns list of items or empty list."""
    if not DIRECTUS_TOKEN:
        return []
    try:
        params: dict = {"limit": str(limit), "fields": fields}
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
    """Update a record in Directus. Returns the response or error."""
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
        # Fallback: if PATCH is forbidden, return a soft error (don't crash)
        if resp.status_code == 403:
            return {"warning": "UPDATE permission not granted, record not updated"}
        return {"error": f"Directus {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"error": f"Directus connection failed: {e}"}


def _find_contact_by_phone(phone: str) -> Optional[dict]:
    """Look up a contact by phone number. Returns the contact dict or None."""
    if not phone:
        return None
    # Normalize: strip spaces, ensure starts with +
    normalized = phone.strip().replace(" ", "")
    results = _directus_read("contacts", {"phone": normalized}, limit=1)
    if results:
        return results[0]
    # Try without + prefix
    if normalized.startswith("+"):
        results = _directus_read("contacts", {"phone": normalized[1:]}, limit=1)
        if results:
            return results[0]
    return None


def _find_company_by_name(name: str) -> Optional[dict]:
    """Look up a company by name. Returns the company dict or None."""
    if not name:
        return None
    results = _directus_read("companies", {"name": name}, limit=1)
    return results[0] if results else None


# ---------------------------------------------------------------------------
# Contact management (upsert)
# ---------------------------------------------------------------------------

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
    If a contact with the same phone number already exists, it will be updated
    instead of creating a duplicate.
    """
    # Normalize phone
    normalized_phone = phone.strip().replace(" ", "") if phone else ""

    # --- Upsert: search by phone first ---
    existing = _find_contact_by_phone(normalized_phone) if normalized_phone else None

    # Build the data payload (only non-empty fields)
    person_data: dict = {}
    if first_name:
        person_data["first_name"] = first_name
    if last_name:
        person_data["last_name"] = last_name
    if email:
        person_data["email"] = email
    if normalized_phone:
        person_data["phone"] = normalized_phone
    if job_title:
        person_data["job_title"] = job_title
    if city:
        person_data["city"] = city
    if product:
        person_data["product"] = product
    if lead_score > 0:
        person_data["lead_score"] = lead_score

    # Link to company if provided
    company_id = None
    if company_name:
        company = _find_company_by_name(company_name)
        if company:
            company_id = company["id"]
        person_data["company"] = company_id or company_name

    if existing:
        # UPDATE existing contact
        contact_id = existing["id"]
        result = _directus_update("contacts", contact_id, person_data)
        action = "UPDATED"
        # If update failed (permissions), still return success with existing ID
        if "warning" in result:
            action = "FOUND (update skipped, check Directus permissions)"
    else:
        # CREATE new contact
        person_data["source"] = "whatsapp"
        person_data["status"] = "lead"
        result = _directus_create("contacts", person_data)
        contact_id = result.get("data", {}).get("id") if "data" in result else None
        action = "CREATED"

    # Log a note event if provided
    if notes:
        event_data: dict = {
            "type": "contact_note",
            "payload": {
                "name": f"{first_name} {last_name}".strip(),
                "product": product,
                "lead_score": lead_score,
                "notes": notes,
            },
        }
        if contact_id:
            event_data["payload"]["contact_id"] = contact_id
        _directus_create("events", event_data)

    if "error" in result:
        return (
            f"CONTACT_{action} (CRM error: {result['error']}): "
            f"{first_name} {last_name}"
        )

    return (
        f"CONTACT_{action}: {first_name} {last_name}"
        f" (id={contact_id})"
        f"{f' ({email})' if email else ''}"
        f"{f' tel:{normalized_phone}' if normalized_phone else ''}"
        f"{f' empresa:{company_name}' if company_name else ''}"
        f" — Registrado en Directus"
    )


# ---------------------------------------------------------------------------
# Company management (upsert)
# ---------------------------------------------------------------------------

@tool()
def save_company(
    name: str,
    domain: str = "",
    employees: int = 0,
    industry: str = "",
    address: str = "",
    notes: str = "",
) -> str:
    """Save or update a company in Directus CRM.

    Call this when a client mentions their company name.
    If a company with the same name already exists, it will be updated.
    """
    existing = _find_company_by_name(name)

    company_data: dict = {"name": name}
    if domain:
        company_data["domain"] = domain
    if employees > 0:
        company_data["employees"] = employees
    if industry:
        company_data["industry"] = industry
    if address:
        company_data["address"] = address

    if existing:
        company_id = existing["id"]
        result = _directus_update("companies", company_id, company_data)
        action = "UPDATED"
        if "warning" in result:
            action = "FOUND (update skipped)"
    else:
        result = _directus_create("companies", company_data)
        company_id = result.get("data", {}).get("id") if "data" in result else None
        action = "CREATED"

    if notes or industry:
        _directus_create(
            "events",
            {
                "type": "company_note",
                "payload": {
                    "company": name,
                    "company_id": company_id,
                    "industry": industry,
                    "notes": notes,
                },
            },
        )

    if "error" in result:
        return f"COMPANY_{action} (CRM error: {result['error']}): {name}"

    return (
        f"COMPANY_{action}: {name} (id={company_id})"
        f"{f' ({domain})' if domain else ''}"
        f" — Registrado en Directus"
    )


# ---------------------------------------------------------------------------
# Payments (with approval + contact linking)
# ---------------------------------------------------------------------------

@approval  # type: ignore[arg-type]
@tool(requires_confirmation=True)
def confirm_payment(
    product: str,
    client_name: str,
    amount: str,
    method: str,
    reference: str = "",
    phone: str = "",
) -> str:
    """Confirm a client payment. Requires human approval before processing.

    Use this when a client says they made a payment or wants to pay.
    The payment will be held until an admin approves it.
    After approval, the payment is logged in Directus CRM and linked to the contact.
    """
    # Find contact to link the payment
    contact_id = None
    if phone:
        contact = _find_contact_by_phone(phone)
        if contact:
            contact_id = contact["id"]

    payment_data: dict = {
        "amount": float(amount) if amount.replace(".", "").replace(",", "").isdigit() else 0,
        "method": method,
        "reference": reference,
        "status": "approved",
        "approved_by": "nexus-agent",
        "product": product,
    }
    if contact_id:
        payment_data["contact_id"] = contact_id

    result = _directus_create("payments", payment_data)

    _directus_create(
        "tasks",
        {
            "title": f"Seguimiento pago: {client_name} ({product})",
            "body": (
                f"Pago de {amount} via {method}. Ref: {reference}. "
                f"Verificar acreditacion."
                f"{f' Contact ID: {contact_id}' if contact_id else ''}"
            ),
            "status": "TODO",
        },
    )

    if "error" in result:
        return (
            f"PAYMENT_APPROVED (CRM error: {result['error']}): "
            f"{client_name} {amount} {method}"
        )

    return (
        f"PAYMENT_CONFIRMED_AND_LOGGED: product={product} client={client_name} "
        f"amount={amount} method={method} ref={reference}"
        f"{f' contact_id={contact_id}' if contact_id else ''}"
        f" — Registrado en Directus"
    )


# ---------------------------------------------------------------------------
# Support tickets (with contact linking)
# ---------------------------------------------------------------------------

@approval(type="audit")
@tool(requires_confirmation=True)
def log_support_ticket(
    product: str,
    intent: str,
    summary: str,
    resolution: str,
    urgency: str = "medium",
    lead_score: int = 0,
    phone: str = "",
) -> str:
    """Log a support interaction to the CRM for tracking and analytics.

    Call this after resolving any customer query to maintain records.
    If the customer's phone is provided, the ticket is linked to their contact.
    """
    # Find contact to link
    contact_id = None
    if phone:
        contact = _find_contact_by_phone(phone)
        if contact:
            contact_id = contact["id"]

    ticket_data: dict = {
        "product": product,
        "intent": intent,
        "summary": summary,
        "resolution": resolution,
        "urgency": urgency,
        "status": "resolved" if resolution else "open",
    }
    if contact_id:
        ticket_data["contact_id"] = contact_id

    result = _directus_create("tickets", ticket_data)

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
        f"lead_score={lead_score}"
        f"{f' contact_id={contact_id}' if contact_id else ''}"
        f" — Registrado en Directus"
    )


# ---------------------------------------------------------------------------
# Escalation
# ---------------------------------------------------------------------------

@tool()
def escalate_to_human(
    product: str,
    reason: str,
    client_name: str = "unknown",
    urgency: str = "high",
    phone: str = "",
) -> str:
    """Escalate a conversation to a human agent.

    Use when: complaint is serious, payment dispute, legal/compliance issue,
    client explicitly asks for a human, or you cannot resolve the issue.
    """
    contact_id = None
    if phone:
        contact = _find_contact_by_phone(phone)
        if contact:
            contact_id = contact["id"]

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
                f"{f'\nContact ID: {contact_id}' if contact_id else ''}"
            ),
            "status": "todo",
        },
    )

    _directus_create(
        "events",
        {
            "type": "escalation",
            "payload": {
                "product": product,
                "client": client_name,
                "contact_id": contact_id,
                "reason": reason,
                "urgency": urgency,
            },
        },
    )

    if "error" in result:
        return (
            f"ESCALATED (CRM error: {result['error']}): "
            f"{product} {client_name} {reason}"
        )

    return (
        f"ESCALATED_AND_LOGGED: product={product} client={client_name} "
        f"urgency={urgency} reason={reason}"
        f"{f' contact_id={contact_id}' if contact_id else ''}"
        f" — Tarea creada en Directus para atencion humana"
    )


# ---------------------------------------------------------------------------
# Conversation logging (with contact linking)
# ---------------------------------------------------------------------------

@tool()
def log_conversation(
    client_name: str,
    product: str,
    channel: str = "whatsapp",
    summary: str = "",
    intent: str = "",
    sentiment: str = "neutral",
    lead_score: int = 0,
    next_action: str = "",
    phone: str = "",
) -> str:
    """Log a complete conversation summary in Directus CRM.

    ALWAYS call this at the END of every conversation. Include:
    - What the client asked about (intent)
    - How the conversation went (sentiment: positive/neutral/negative)
    - What to do next (next_action)
    - Lead score if applicable
    - Phone number to link to the contact record
    """
    contact_id = None
    if phone:
        contact = _find_contact_by_phone(phone)
        if contact:
            contact_id = contact["id"]

    conversation_data: dict = {
        "channel": channel,
        "direction": "inbound",
        "raw_message": summary,
        "agent_response": next_action or "",
        "intent": intent,
        "sentiment": sentiment,
        "lead_score": lead_score,
        "agent_name": "qyne-support",
    }
    if contact_id:
        conversation_data["contact_id"] = contact_id

    result = _directus_create("conversations", conversation_data)

    if next_action:
        _directus_create(
            "tasks",
            {
                "title": f"Seguimiento: {client_name} ({product})",
                "body": f"Accion: {next_action}\nContexto: {summary[:200]}",
                "status": "todo",
            },
        )

    if "error" in result:
        return f"CONVERSATION_LOGGED (CRM error: {result['error']}): {client_name}"

    return (
        f"CONVERSATION_LOGGED: {client_name} ({product}) via {channel} "
        f"intent={intent} sentiment={sentiment} score={lead_score}"
        f"{f' contact_id={contact_id}' if contact_id else ''}"
        f" — Registrado en Directus"
    )
