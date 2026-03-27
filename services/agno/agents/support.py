"""
QYNE v1 — Support Agent.

Handles customer support via WhatsApp and chat.
Writes to Directus via REST tools (directus_business.py).
"""

import os

from agno.agent import Agent

from app.config import TOOL_MODEL, FOLLOWUP_MODEL, DIRECTUS_URL, DIRECTUS_TOKEN, db
from app.shared import guardrails, learning_full, compression
from tools.directus_business import (
    confirm_payment,
    log_support_ticket,
    escalate_to_human,
    save_contact,
    save_company,
)

support_agent = Agent(
    name="Support Agent",
    id="support-agent",
    role="Customer support specialist for Whabi, Docflow, and Aurora",
    model=TOOL_MODEL,
    tools=[confirm_payment, log_support_ticket, escalate_to_human, save_contact, save_company],
    tool_call_limit=8,
    retries=2,
    pre_hooks=guardrails,
    instructions=[
        "You are the customer support specialist for AikaLabs.",
        "You handle support for three products: Whabi (WhatsApp CRM), Docflow (EHR), and Aurora (voice-first PWA).",
        "ALWAYS greet warmly in Spanish. Be professional but friendly.",
        "When a customer identifies themselves, IMMEDIATELY save their contact info.",
        "For payments, ALWAYS use confirm_payment (requires human approval).",
        "For serious complaints or legal issues, use escalate_to_human.",
        "Log every interaction with log_support_ticket for analytics.",
        "If you cannot resolve an issue, escalate to a human agent.",
    ],
    db=db,
    learning=learning_full,
    add_history_to_context=True,
    num_history_runs=5,
    add_datetime_to_context=True,
    update_memory_on_run=True,
    markdown=True,
    followups=True,
    num_followups=3,
    followup_model=FOLLOWUP_MODEL,
    compression_manager=compression,
)
