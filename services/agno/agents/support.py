"""
NEXUS Cerebro — Support Agent.

Handles customer support via WhatsApp and chat.
Integrates with Directus CRM via MCP for reading/writing customer data.
Uses full learning (profile, memory, entities) to remember customers.
"""

import os

from agno.agent import Agent
from agno.tools.mcp import MCPTools

from app.config import TOOL_MODEL, FOLLOWUP_MODEL, DIRECTUS_URL, DIRECTUS_TOKEN, db
from app.shared import guardrails, learning_full, compression
from tools.directus_business import (
    confirm_payment,
    log_support_ticket,
    escalate_to_human,
    save_contact,
    save_company,
)

# Directus MCP tools (auto-discovers collections, respects RBAC)
_directus_mcp_url = f"{DIRECTUS_URL}/mcp"

# Build tool list: business logic tools + MCP for generic CRUD
_tools = [confirm_payment, log_support_ticket, escalate_to_human, save_contact, save_company]

# Add Directus MCP if token is configured
if DIRECTUS_TOKEN:
    _tools.append(
        MCPTools(
            url=_directus_mcp_url,
            headers={"Authorization": f"Bearer {DIRECTUS_TOKEN}"},
        )
    )

support_agent = Agent(
    name="Support Agent",
    id="support-agent",
    role="Customer support specialist for Whabi, Docflow, and Aurora",
    model=TOOL_MODEL,
    tools=_tools,
    tool_call_limit=8,
    retries=2,
    pre_hooks=guardrails,
    instructions=[
        "You are the customer support specialist for AikaLabs.",
        "You handle support for three products: Whabi (WhatsApp CRM), Docflow (EHR), and Aurora (voice-first PWA).",
        "ALWAYS greet warmly in Spanish. Be professional but friendly.",
        "When a customer identifies themselves, IMMEDIATELY save their contact info.",
        "Use the Directus MCP tools to read and write customer data.",
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
